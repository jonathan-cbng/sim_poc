import argparse
import asyncio
import json
import logging

import zmq
import zmq.asyncio

from src.config import settings

logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(levelname)s: %(asctime)s %(filename)s - %(message)s",
)


class APWorker:
    def __init__(self, network_idx, hub_idx, ap_idx, pub_addr, pull_addr):
        self.network_idx = network_idx
        self.hub_idx = hub_idx
        self.ap_idx = ap_idx
        self.tag = f"NET{network_idx:04d}HUB{hub_idx:04d}AP{ap_idx:04d}"
        self.ctx = zmq.asyncio.Context()
        # Set up PUB socket (for receiving commands)
        self.pub_sock = self.ctx.socket(zmq.SUB)
        self.pub_sock.connect(pub_addr)
        self.pub_sock.setsockopt_string(zmq.SUBSCRIBE, self.tag)
        # Set up PUSH socket (for sending status)
        self.push_sock = self.ctx.socket(zmq.PUSH)
        self.push_sock.connect(pull_addr)

    async def execute_command(self, command: dict):
        """
        Execute a command received from the controller.
        This is a stub implementation; in a real AP, this would perform actions.
        """
        if not command:
            logging.warning(f"[AP Worker {self.tag}] No command to execute.")
            return
        event = command.get("event")
        match event:
            case "register_ap_to_nms":
                logging.info(f"[AP Worker {self.tag}] Registering AP to NMS (stub).")
                # Simulate sending a registration confirmation back
                response = json.dumps(
                    {"event": "ap_registered", "net": self.network_idx, "hub": self.hub_idx, "ap": self.ap_idx}
                )
                await self.push_sock.send_string(response)
            case _:
                logging.warning(f"[AP Worker {self.tag}] Unknown command event: {event}")
        return

    def decode_message(self, message: str):
        """
        Process a message received from the controller.
        Expected format: '<subscriber_tag> <json_message>'
        """
        try:
            json_part = message.split(" ", 1)[1]
            data = json.loads(json_part)
            logging.info(f"[AP Worker {self.tag}] received message': {data}")
            return data
        except json.JSONDecodeError as e:
            logging.error(f"[AP Worker {self.tag}] JSON decode error: {e} in message: {message}")
            return None
        except ValueError:
            logging.error(f"[AP Worker {self.tag}] Malformed message (no space found): {message}")
            return None

    async def read_loop(self):
        # Send 'connected' message with separate fields
        msg = json.dumps({"event": "ap_connected", "net": self.network_idx, "hub": self.hub_idx, "ap": self.ap_idx})
        await self.push_sock.send_string(msg)
        # Main loop: wait for messages from controller
        while True:
            try:
                message = await self.pub_sock.recv_string()
                logging.debug(f"[AP Worker {self.tag}] Received command: {message}")
                command = self.decode_message(message)
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
