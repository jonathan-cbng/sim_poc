import argparse
import asyncio
import logging
from datetime import UTC, datetime

import httpx
import shortuuid
import zmq
import zmq.asyncio

from src.api_nms import (
    NmsAPCreateRequest,
    NmsAuthInfo,
    RegisterAPCandidateHeaders,
    RegisterAPCandidateRequest,
    RegisterAPSecretHeaders,
)
from src.config import settings
from src.worker.worker_api import Address, APRegisterReq, APRegisterRsp, HubConnectInd, Message, MessageTypes

logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(levelname)s: %(asctime)s %(filename)s:%(lineno)d - %(message)s",
)


class Uplink:
    def __init__(self, address: Address, pull_addr, ctx: zmq.asyncio.Context):
        # Set up PUSH socket (for sending status)
        self.address = address
        self.push_sock = ctx.socket(zmq.PUSH)
        self.push_sock.connect(pull_addr)

    async def send_to_controller(self, msg):
        """
        Send a message to the controller.
        Wraps the payload in a Message root model for correct encoding.
        """
        # Wrap this message in the Message root model if not already done
        msg = msg if isinstance(msg, Message) else Message(msg)
        payload = (
            f"{self.address.tag}: {msg.model_dump_json()}"  # not strictly necessary but makes it symmetric with pub
        )
        await self.push_sock.send_string(payload)
        logging.debug("Tx %s->controller: %r", self.address.tag, msg.root)


nodes: dict[Address, ["AP", "RT"]] = {}


class Node:
    def __init__(self, address, uplink: Uplink):
        self.uplink = uplink
        self.address = address
        nodes[self.address] = self

    def __del__(self):
        del nodes[self.address]


class RT(Node):
    def __init__(self, address, uplink: Uplink):
        """
        Class representing a Remote Terminal (RT) in the network simulation.
        """
        super().__init__(address, uplink)
        self.parent_auid = None
        self.heartbeat_secs = None
        self.auid = None


class AP(Node):
    """
    Class representing an Access Point (AP) in the network simulation.
    """

    def __init__(self, address, uplink: Uplink):
        super().__init__(address, uplink)
        self.parent_auid = None
        self.heartbeat_secs = None
        self.auid = None
        self.azimuth_deg = None
        self.ap_secret = None

    async def process_register_req(self, command: APRegisterReq):
        """
        Handle an AP registration request.

        Registration process overview:
        1. The AP is created in the NBAPI (Network Backend API) with its configuration and parent hub.
        2. The AP's secret is registered with the SBAPI (Service Backend API) using the AP's AUID and secret.
        3. The AP is registered as a candidate in the SBAPI, providing the customer CSI, installer key, and chosen AUID.
        4. If any step fails, the registration process is aborted for this AP.
        5. On success, the AP is considered registered and ready for further provisioning.

        This method performs the registration and sends an APRegisterInd message back to the controller on success.
        """
        self.parent_auid = command.hub_auid
        self.heartbeat_secs = command.heartbeat_seconds
        self.auid = command.auid
        self.azimuth_deg = command.azimuth_deg
        self.ap_secret = shortuuid.uuid()

        temp_auid = f"T-{self.auid}"
        # Compose AP creation payload using Pydantic model
        ap_payload = NmsAPCreateRequest(
            auid=temp_auid,
            id=f"ID_{self.auid}",
            name=f"NAME_{self.auid}",
            parent_auid=self.parent_auid,
            azimuth_deg=self.azimuth_deg,
        )

        try:
            async with httpx.AsyncClient(
                timeout=settings.HTTPX_TIMEOUT, verify=settings.VERIFY_SSL_CERT, follow_redirects=True
            ) as client:
                # Step 1: Create AP in NBAPI
                res = await client.post(
                    f"{settings.NBAPI_URL}/api/v1/node/ap/{temp_auid}",
                    json=ap_payload.model_dump(),
                    headers=NmsAuthInfo().auth_header(),
                )
                res.raise_for_status()

                # Step 2: Register AP secret in SBAPI using Pydantic headers
                secret_headers = RegisterAPSecretHeaders(gnodebid=self.auid, secret=self.ap_secret)
                res = await client.post(
                    f"{settings.SBAPI_URL}/ap/register_secret/", json={}, headers=secret_headers.model_dump()
                )
                res.raise_for_status()

                # Step 3: Register AP as candidate in SBAPI using Pydantic models
                candidate_payload = RegisterAPCandidateRequest(
                    csi=settings.CSI,
                    installer_key=settings.INSTALLER_KEY,
                    chosen_auid=temp_auid,
                )
                candidate_headers = RegisterAPCandidateHeaders(gnodebid=self.auid, secret=self.ap_secret)
                res = await client.post(
                    f"{settings.SBAPI_URL}/ap/register_candidate",
                    json=candidate_payload.model_dump(),
                    headers=candidate_headers.model_dump(),
                )
                res.raise_for_status()

                # Registration successful
                logging.info("%s: AP registration successful (AUID: %s)", self.address.tag, self.auid)
        except Exception as e:
            logging.error(f"Exception during AP registration: {e}")
            return

        response = APRegisterRsp(address=self.address, registered_at=datetime.now(UTC).isoformat())
        await self.uplink.send_to_controller(response)


class Worker:
    """Top level worker class that simulates a network hub.

    Up to 32 APs can be simulated per hub, each with up to 64 RTs."""

    def __init__(self, network_idx, hub_idx, pub_addr, pull_addr):
        self.zmq_context = zmq.asyncio.Context()
        self.address = Address(net=network_idx, hub=hub_idx)
        self.auid = str(shortuuid.uuid())
        self.pub_addr = pub_addr
        self.uplink = Uplink(self.address, pull_addr, self.zmq_context)

    async def process_register_req(self, command: APRegisterReq):
        ap = AP(self.address, self.uplink)
        await ap.process_register_req(command)

    async def execute_command(self, command: Message):
        """
        Execute a command received from the controller.
        Uses Pydantic message classes for decoding/encoding.
        """
        cmd = command.root
        logging.debug("Rx ctrl->%s: %r", self.address.tag, cmd)
        obj = nodes.get(cmd.address, self)
        match cmd.msg_type:
            case MessageTypes.AP_REGISTER_REQ:
                await obj.process_register_req(cmd)
            case _:
                logging.warning(f"[AP Worker {self.address.tag}] Unknown command event: {cmd.msg_type}")

    def decode_message(self, message: str) -> Message | None:
        """
        Process a message received from the controller.
        Expected format: '<subscriber_tag> <json_message>'
        Uses Pydantic Message.model_validate_json for decoding.
        """
        try:
            json_part = message.split(" ", 1)[1]
            data = Message.model_validate_json(json_part)
            return data
        except Exception as e:
            logging.error(f"[AP Worker {self.address.tag}] Error decoding message: {e} in message: {message}")
            return None

    async def downlink_loop(self):
        await self.uplink.send_to_controller(HubConnectInd(address=self.address))
        # Set up PUB socket (for receiving commands)
        pub_sock = self.zmq_context.socket(zmq.SUB)
        pub_sock.connect(self.pub_addr)
        pub_sock.setsockopt_string(zmq.SUBSCRIBE, self.address.tag)

        logging.debug("%s starting read loop", self.address.tag)
        # Main loop: wait for messages from controller
        while True:
            try:
                message = await pub_sock.recv_string()
                command = self.decode_message(message)
                if command is not None:
                    await self.execute_command(command)
            except Exception as e:
                logging.error(f"[AP Worker {self.address.tag}] Error receiving command: {e}")
                await asyncio.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AP Worker Stub")
    parser.add_argument("network_idx", type=int)
    parser.add_argument("hub_idx", type=int)
    parser.add_argument("pub_addr", type=str)
    parser.add_argument("pull_addr", type=str)
    args = parser.parse_args()
    worker = Worker(args.network_idx, args.hub_idx, args.pub_addr, args.pull_addr)
    asyncio.run(worker.downlink_loop())
