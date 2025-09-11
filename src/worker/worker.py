import argparse
import asyncio
import logging

import zmq
import zmq.asyncio

from src.config import settings
from src.worker.accel import AP
from src.worker.api import ApAddress, APConnectInd, APRegisterInd, APRegisterReq, Message, MessageTypes

logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(levelname)s: %(asctime)s %(filename)s:%(lineno)d - %(message)s",
)


class APWorker(AP):
    def __init__(self, network_idx, hub_idx, ap_idx, pub_addr, pull_addr):
        super().__init__()
        self.ap_address = ApAddress(net=network_idx, hub=hub_idx, ap=ap_idx)
        self.tag = f"NET{network_idx:04d}HUB{hub_idx:04d}AP{ap_idx:04d}"
        self.ctx = zmq.asyncio.Context()
        # Set up PUB socket (for receiving commands)
        self.pub_sock = self.ctx.socket(zmq.SUB)
        self.pub_sock.connect(pub_addr)
        self.pub_sock.setsockopt_string(zmq.SUBSCRIBE, self.tag)
        # Set up PUSH socket (for sending status)
        self.push_sock = self.ctx.socket(zmq.PUSH)
        self.push_sock.connect(pull_addr)

    async def send_to_controller(self, msg):
        """
        Send a message to the controller.
        Wraps the payload in a Message root model for correct encoding.
        """
        # Wrap this message in the Message root model if not already done
        msg = msg if isinstance(msg, Message) else Message(msg)
        payload = f"{self.tag:} {msg.model_dump_json()}"  # not strictly necessary but makes it symmetric with pub
        await self.push_sock.send_string(payload)
        logging.debug("Tx %s->controller: %r", self.tag, msg.root)

    async def process_register_req(self, command: APRegisterReq):
        logging.info("%s: Processing register request (stub).", self.tag)
        # Simulate sending a registration confirmation back
        response = APRegisterInd(ap_address=self.ap_address, registered_at="2025-09-08T12:00:00Z")
        await self.send_to_controller(response)

    async def execute_command(self, command: Message):
        """
        Execute a command received from the controller.
        Uses Pydantic message classes for decoding/encoding.
        """
        cmd = command.root
        logging.debug("Rx ctrl->%s: %r", self.tag, cmd)
        match cmd.msg_type:
            case MessageTypes.AP_REGISTER_REQ:
                await self.process_register_req(cmd)
            case _:
                logging.warning(f"[AP Worker {self.tag}] Unknown command event: {cmd.msg_type}")

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
            logging.error(f"[AP Worker {self.tag}] Error decoding message: {e} in message: {message}")
            return None

    async def read_loop(self):
        # Send 'connected' message using Pydantic class
        msg = APConnectInd(ap_address=self.ap_address)
        await self.send_to_controller(msg)
        # Main loop: wait for messages from controller
        while True:
            try:
                message = await self.pub_sock.recv_string()
                command = self.decode_message(message)
                if command is not None:
                    await self.execute_command(command)
            except Exception as e:
                logging.error(f"[AP Worker {self.tag}] Error receiving command: {e}")
                await asyncio.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AP Worker Stub")
    parser.add_argument("network_idx", type=int)
    parser.add_argument("hub_idx", type=int)
    parser.add_argument("ap_idx", type=int)
    parser.add_argument("pub_addr", type=str)
    parser.add_argument("pull_addr", type=str)
    args = parser.parse_args()
    worker = APWorker(args.network_idx, args.hub_idx, args.ap_idx, args.pub_addr, args.pull_addr)
    asyncio.run(worker.read_loop())
