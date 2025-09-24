"""
worker.py

Simulates a network hub worker that manages Access Points (APs) and Remote Terminals (RTs) within a hub.

This module defines the Worker class, which is responsible for handling commands from a controller, managing
APs, and facilitating communication between the controller and APs/RTs. The worker communicates using the
ControllerLink and processes messages using Pydantic models.

Usage:
    python worker.py <network_idx> <hub_idx> <pub_addr> <pull_addr>

Args:
    network_idx (int): Network index for the hub address.
    hub_idx (int): Hub index for the hub address.
    pub_addr (str): Address for publishing messages to the controller.
    pull_addr (str): Address for pulling messages from the controller.
"""
#######################################################################################################################
# Imports
#######################################################################################################################

import argparse
import asyncio
import logging

import httpx
import shortuuid

from src.config import settings
from src.worker.ap import AP
from src.worker.comms import WorkerComms
from src.worker.node import Node, nodes
from src.worker.rt import RT
from src.worker.utils import fix_execution_time
from src.worker.worker_api import Address, APRegisterReq, HubConnectInd, Message, MessageTypes, RTRegisterReq

#######################################################################################################################
# Globals
#######################################################################################################################

logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(levelname)s: %(asctime)s %(filename)s:%(lineno)d - %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Suppress httpx debug amd info logs
#######################################################################################################################
# Body
#######################################################################################################################


class Hub(Node):
    """Top level worker class that simulates a network hub.

    An arbitrary number of APs and RTs can be created within the hub, but for practical
    purposes we expect each hub to have up to 32 APs, each with up to 64 RTs.

    Args:
        address (Address): The address of the hub.
        comms (WorkerComms): Communication link to the controller.
    """

    def __init__(self, address: Address, comms: WorkerComms):
        """Initializes the Worker.

        Args:
            address (Address): The address of the hub.
            comms (WorkerComms): Communication link to the controller.
        """
        http_client = httpx.AsyncClient(
            timeout=settings.HTTPX_TIMEOUT,
            verify=settings.VERIFY_SSL_CERT,
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=settings.WORKER_HTTPX_POOLSIZE, max_keepalive_connections=settings.WORKER_HTTPX_POOLSIZE
            ),
        )
        super().__init__(address, comms, http_client)
        self.auid = str(shortuuid.uuid())
        self.comms = comms

    async def ap_register_req(self, command: APRegisterReq) -> Message | None:
        """Process an AP register request. We handle this at the worker level to create
        the AP object and then delegate to it.

        Args:
            command (APRegisterReq): The AP register request message.

        Returns:
            Message: The response message from the AP.
        """
        ap = AP(command.address, self.comms, self.http_client)
        return await ap.on_register_req(command)

    async def rt_register_req(self, command: RTRegisterReq) -> Message | None:
        """Process an AP register request. We handle this at the worker level to create
        the AP object and then delegate to it.

        Args:
            command (APRegisterReq): The AP register request message.

        Returns:
            Message: The response message from the AP.
        """

        rt = RT(command.address, self.comms, self.http_client)
        return await rt.on_rt_register_req(command)

    async def execute_command(self, command: Message) -> None:
        """Execute a command received from the controller.

        Uses Pydantic message classes for decoding/encoding.

        Args:
            command (Message): The message received from the controller.
        """
        cmd = command.root
        logging.debug(f"Rx ctrl->{self.address.tag}: {cmd!r}")
        obj: Hub | RT | AP = nodes.get(cmd.address, self)
        result = None
        match cmd.msg_type:
            case MessageTypes.AP_REGISTER_REQ:
                result = await obj.ap_register_req(cmd)
            case MessageTypes.RT_REGISTER_REQ:
                result = await obj.rt_register_req(cmd)
            case MessageTypes.START_HEARTBEAT_REQ:
                result = await obj.on_start_heartbeat_req()
            case MessageTypes.HEARTBEAT_STATS_REQ:
                result = obj.on_heartbeat_stats_req()
            case _:
                logging.warning(f"[AP Worker {self.address.tag}] Unknown command event: {cmd.msg_type}")

        if result is not None:
            await self.comms.send_msg(result)

    async def reporter_loop(self):
        """Periodically report the status of the hub and its APs/RTs to the controller."""
        while True:
            async with fix_execution_time(settings.REPORTER_INTERVAL):
                # Implement reporting logic here if needed
                logging.info(f"Hub {self.address.tag} Heartbeat summary: {self.heartbeat_state.children}")

    async def downlink_loop(self, max_concurrent: int = settings.MAX_CONCURRENT_WORKER_COMMANDS) -> None:
        """Main loop: wait for messages from controller and process them concurrently, limiting in-flight commands."""
        asyncio.create_task(self.reporter_loop())
        await self.comms.send_msg(HubConnectInd(address=self.address))

        logging.debug(f"{self.address.tag} starting read loop")
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = set()

        async def handle_command(command):
            async with semaphore:
                try:
                    await self.execute_command(command)
                except Exception:
                    logging.error(f"[AP Worker {self.address.tag}] Error processing command", exc_info=True)

        while True:
            try:
                command = await self.comms.recv_msg()
                if command is not None:
                    task = asyncio.create_task(handle_command(command))
                    tasks.add(task)
                    task.add_done_callback(tasks.discard)
            except Exception:
                logging.error(f"[Hub Worker {self.address.tag}] Error receiving command", exc_info=True)
                await asyncio.sleep(1)

    async def close(self):
        """Clean up resources before closing the worker."""
        await self.http_client.aclose()


def main() -> None:
    """Entry point for the worker script."""
    parser = argparse.ArgumentParser(description="AP Worker Stub")
    parser.add_argument("network_idx", type=int)
    parser.add_argument("hub_idx", type=int)
    parser.add_argument("pub_addr", type=str)
    parser.add_argument("pull_addr", type=str)
    args = parser.parse_args()
    address = Address(net=args.network_idx, hub=args.hub_idx)
    comms = WorkerComms(address, args.pull_addr, args.pub_addr)
    worker = Hub(address, comms)
    try:
        asyncio.run(worker.downlink_loop())
    except KeyboardInterrupt:
        logging.info("Worker stopped by user")
    finally:
        asyncio.run(worker.close())


if __name__ == "__main__":
    main()

#######################################################################################################################
# End of file
#######################################################################################################################
