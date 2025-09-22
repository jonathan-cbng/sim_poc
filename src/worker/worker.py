import argparse
import asyncio
import logging

import shortuuid

from src.config import settings
from src.worker.ap import AP
from src.worker.comms import ControllerLink
from src.worker.node import nodes
from src.worker.worker_api_types import Address, APRegisterReq, HubConnectInd, Message, MessageTypes

logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(levelname)s: %(asctime)s %(filename)s:%(lineno)d - %(message)s",
)


class Worker:
    """Top level worker class that simulates a network hub.

    An arbitrary number of APs and RTs can be created within the hub, but for practical
    purposes we expect each hub to have a up to 32 APs, each with up to 64 RTs.
    """

    def __init__(self, address, comms: ControllerLink):
        self.address = address
        self.auid = str(shortuuid.uuid())
        self.comms = comms

    async def process_register_req(self, command: APRegisterReq):
        ap = AP(command.address, self.comms)
        return await ap.process_register_req(command)

    async def execute_command(self, command: Message):
        """
        Execute a command received from the controller.
        Uses Pydantic message classes for decoding/encoding.
        """
        cmd = command.root
        logging.debug("Rx ctrl->%s: %r", self.address.tag, cmd)
        obj = nodes.get(cmd.address, self)
        result = None
        match cmd.msg_type:
            case MessageTypes.AP_REGISTER_REQ:
                result = await obj.process_register_req(cmd)
            case _:
                logging.warning(f"[AP Worker {self.address.tag}] Unknown command event: {cmd.msg_type}")

        if result is not None:
            await self.comms.send_to_controller(result)

    async def downlink_loop(self):
        await self.comms.send_to_controller(HubConnectInd(address=self.address))

        logging.debug("%s starting read loop", self.address.tag)
        # Main loop: wait for messages from controller
        while True:
            try:
                command = await self.comms.get_command()
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
    address = Address(net=args.network_idx, hub=args.hub_idx)
    comms = ControllerLink(address, args.pull_addr, args.pub_addr)
    worker = Worker(address, comms)
    asyncio.run(worker.downlink_loop())
