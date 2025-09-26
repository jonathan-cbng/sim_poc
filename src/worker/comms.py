"""
comms.py

Manages communication between an AP worker and the controller using ZeroMQ sockets.

This module provides the WorkerComms class, which sets up ZeroMQ PUSH and SUB sockets for sending status updates to
the controller and receiving commands from the controller, respectively. The SUB socket subscribes to messages tagged
with the address tag (e.g., "N01H02").

Usage:
    Used internally by the worker process to send status and receive commands via ZeroMQ.
"""
#######################################################################################################################
# Imports
#######################################################################################################################

import logging

import zmq
import zmq.asyncio

from src.worker.worker_api import Address, Message

#######################################################################################################################
# Globals
#######################################################################################################################

#######################################################################################################################
# Body
#######################################################################################################################


class WorkerComms:
    """
    Manages communication between an AP worker and the controller using ZeroMQ.

    Uses a PUSH socket to send status updates to the controller and a SUB socket to receive commands
    from the controller. The SUB socket subscribes to messages tagged with the address tag provided
    (in our case, this is expected to be the Hub tag, e.g. "n0001h0002").

    Args:
        address (Address): The address of the worker node.
        pull_addr (str): Address for the controller's PULL socket (for status updates).
        pub_addr (str): Address for the controller's PUB socket (for commands).
    """

    def __init__(self, address: Address, pull_addr: str, pub_addr: str):
        """
        Initialize the WorkerComms instance and set up ZeroMQ sockets.

        Args:
            address (Address): The address of the worker node.
            pull_addr (str): Address for the controller's PULL socket (for status updates).
            pub_addr (str): Address for the controller's PUB socket (for commands).
        """
        ctx = zmq.asyncio.Context()
        self.address = address
        # This is for sending status updates to the controller
        self.push_sock = ctx.socket(zmq.PUSH)
        self.push_sock.connect(pull_addr)

        # This is for receiving commands from the controller
        self.pub_sock = ctx.socket(zmq.SUB)
        self.pub_sock.connect(pub_addr)
        self.pub_sock.setsockopt_string(zmq.SUBSCRIBE, self.address.tag)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.push_sock.close(linger=0)
        self.pub_sock.close(linger=0)
        self.ctx.term()

    async def send_msg(self, msg) -> None:
        """
        Send a message to the controller.

        Wraps the payload in a Message root model for correct encoding.

        Args:
            msg: The message or payload to send (Message or compatible type).
        """
        msg = msg if isinstance(msg, Message) else Message(msg)
        payload = f"{self.address.tag}: {msg.model_dump_json()}"
        await self.push_sock.send_string(payload)
        logging.debug("Tx %s->controller: %r", self.address.tag, msg.root)

    async def recv_msg(self) -> Message | None:
        """
        Receive and decode a command from the controller.

        Returns:
            Message | None: The decoded Message object, or None if decoding fails.
        """
        message = await self.pub_sock.recv_string()
        data = None
        try:
            json_part = message.split(" ", 1)[1]
            data = Message.model_validate_json(json_part).root
        except Exception as e:
            logging.error(f"[AP Worker {self.address.tag}] Error decoding message: {e} in message: {message}")
        return data


#######################################################################################################################
# End of file
#######################################################################################################################
