import logging

import zmq
import zmq.asyncio

from src.worker.api_types import Address, Message


class WorkerComms:
    """
    Class to manage communication between an AP worker and the controller using ZeroMQ.
    Uses a PUSH socket to send status updates to the controller and a SUB socket to receive commands
    from the controller. The SUB socket subscribes to messages tagged with the address tag provided
    (in our case, this is expected to be the Hub tag, e.g. "n0001h0002").
    """

    def __init__(self, address: Address, pull_addr: str, pub_addr: str):
        # Set up PUSH socket (for sending status)
        ctx = zmq.asyncio.Context()
        self.address = address
        self.push_sock = ctx.socket(zmq.PUSH)
        self.push_sock.connect(pull_addr)
        # Set up PUB socket (for receiving commands)
        self.pub_sock = ctx.socket(zmq.SUB)
        self.pub_sock.connect(pub_addr)
        self.pub_sock.setsockopt_string(zmq.SUBSCRIBE, self.address.tag)

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

    async def get_command(self) -> Message:
        """
        Receive and decode a command from the controller.
        """
        message = await self.pub_sock.recv_string()
        data = None
        try:
            json_part = message.split(" ", 1)[1]
            data = Message.model_validate_json(json_part)
        except Exception as e:
            logging.error(f"[AP Worker {self.address.tag}] Error decoding message: {e} in message: {message}")

        return data
