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
    RegisterAPCandidateHeaders,
    RegisterAPCandidateRequest,
    RegisterAPSecretHeaders,
)
from src.config import settings
from src.worker.worker_api import Address, APRegisterInd, APRegisterReq, HubConnectInd, Message, MessageTypes

logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(levelname)s: %(asctime)s %(filename)s:%(lineno)d - %(message)s",
)


class AP:
    def __init__(self, network_idx, hub_idx, ap_idx):
        self.address = Address(net=network_idx, hub=hub_idx, ap=ap_idx)


class Worker:
    """Top level worker class that simulates a network hub.

    Up to 32 APs can be simulated per hub, each with up to 64 RTs."""

    def __init__(self, network_idx, hub_idx, pub_addr, pull_addr):
        super().__init__()
        self.address = Address(net=network_idx, hub=hub_idx)
        self.ctx = zmq.asyncio.Context()
        # Set up PUB socket (for receiving commands)
        self.pub_sock = self.ctx.socket(zmq.SUB)
        self.pub_sock.connect(pub_addr)
        self.pub_sock.setsockopt_string(zmq.SUBSCRIBE, self.address.tag)
        # Set up PUSH socket (for sending status)
        self.push_sock = self.ctx.socket(zmq.PUSH)
        self.push_sock.connect(pull_addr)

        self.auid = str(shortuuid.uuid())

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

        # Gather config
        # NBAPI_URL = settings.NBAPI_URL
        # SBAPI_URL = settings.SBAPI_URL
        # NBAPI_AUTH = settings.NBAPI_AUTH
        # CSI = settings.CSI
        #
        # INSTALLER_KEY = settings.INSTALLER_KEY
        # VERIFY_SSL_CERT = settings.VERIFY_SSL_CERT
        # AP_SECRET = settings.AP_SECRET

        parent_auid = command.hub_auid
        ap_auid = self.address.tag
        temp_auid = f"T-{ap_auid}"
        # Compose AP creation payload using Pydantic model
        ap_payload = NmsAPCreateRequest(
            auid=temp_auid,
            id=f"ID_{ap_auid}",
            name=f"NAME_{ap_auid}",
            parent_auid=parent_auid,
            azimuth_deg=round(self.address.ap * (360 / command.num_rts)),
        )

        try:
            async with httpx.AsyncClient(timeout=settings.HTTPX_TIMEOUT) as client:
                # Step 1: Create AP in NBAPI
                nbapi_url = f"{settings.NBAPI_URL}/api/v1/node/ap/T-{ap_auid}"
                async with client.post(
                    nbapi_url,
                    json=ap_payload.model_dump(),
                    headers={"Authorization": settings.NBAPI_AUTH},
                    verify=settings.VERIFY_SSL_CERT,
                ) as res:
                    res.raise_for_status("AP creation failed")

                # Step 2: Register AP secret in SBAPI using Pydantic headers
                sbapi_secret_url = f"{settings.SBAPI_URL}/ap/register_secret"
                secret_headers = RegisterAPSecretHeaders(gnodebid=ap_auid, secret=settings.AP_SECRET)
                async with client.post(
                    sbapi_secret_url, json={}, headers=secret_headers.model_dump(), verify=settings.VERIFY_SSL_CERT
                ) as res:
                    res.raise_for_status("AP secret registration failed")

                # Step 3: Register AP as candidate in SBAPI using Pydantic models
                sbapi_candidate_url = f"{settings.SBAPI_URL}/ap/register_candidate"
                candidate_payload = RegisterAPCandidateRequest(
                    csi=settings.CSI,
                    installer_key=settings.INSTALLER_KEY,
                    chosen_auid=f"T-{ap_auid}",
                )
                candidate_headers = RegisterAPCandidateHeaders(gnodebid=ap_auid, secret=settings.AP_SECRET)
                async with client.post(
                    sbapi_candidate_url,
                    json=candidate_payload.model_dump(),
                    headers=candidate_headers.model_dump(),
                    verify=settings.VERIFY_SSL_CERT,
                ) as res:
                    res.raise_for_status("AP candidate registration failed")

                # Registration successful
                logging.info("%s: AP registration successful (AUID: %s)", self.address.tag, ap_auid)
        except Exception as e:
            logging.error(f"Exception during AP registration: {e}")
            return

        response = APRegisterInd(address=self.address, registered_at=datetime.now(UTC).isoformat())
        await self.send_to_controller(response)

    async def execute_command(self, command: Message):
        """
        Execute a command received from the controller.
        Uses Pydantic message classes for decoding/encoding.
        """
        cmd = command.root
        logging.debug("Rx ctrl->%s: %r", self.address.tag, cmd)
        match cmd.msg_type:
            case MessageTypes.AP_REGISTER_REQ:
                await self.process_register_req(cmd)
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

    async def read_loop(self):
        await self.send_to_controller(HubConnectInd(address=self.address))
        logging.debug("%s starting read loop", self.address.tag)
        # Main loop: wait for messages from controller
        while True:
            try:
                message = await self.pub_sock.recv_string()
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
    asyncio.run(worker.read_loop())
