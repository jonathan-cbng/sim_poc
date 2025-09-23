"""
comms.py

Manages communication between the controller and worker nodes using ZeroMQ sockets.

This module provides the ControllerComms class, which sets up ZeroMQ PUB and PULL sockets for sending commands to
workers and receiving status updates from workers, respectively. The PUB socket is used to send commands to worker
nodes, and the PULL socket is used to receive status updates from them. The class also provides methods for setting
up and tearing down the ZeroMQ context and sockets.

Usage:
    Used internally by the controller process to communicate with worker nodes via ZeroMQ.
"""
#######################################################################################################################
# Imports
#######################################################################################################################

import logging

import zmq
import zmq.asyncio

from src.worker.worker_api import Message

#######################################################################################################################
# Body
#######################################################################################################################


class ControllerComms:
    """
    Manages communication between the controller and worker nodes using ZeroMQ.

    Uses a PUB socket to send commands to workers and a PULL socket to receive status updates from workers.

    Args:
        None
    """

    def __init__(self):
        self.zmq_ctx = zmq.asyncio.Context()

    async def get_message(self) -> Message | None:
        """
        Receive a message from a worker node via the PULL socket.

        Returns:
            Message: The received message.
        """
        msg_bytes = await self.zmq_pull.recv()
        tag, msg_bytes = msg_bytes.split(b" ", 1)

        try:
            msg = Message.model_validate_json(msg_bytes)
            msg = msg.root  # This is the actual message inside the wrapper.
            logging.debug("Rx %s->ctrl: %r", str(tag), msg)
            return msg
        except Exception as e:
            logging.warning(f"Unable to decode message: {msg_bytes!r} ({e})")
            return None

    def send(self, msg) -> None:
        """
        Send a message to a worker node via the PUB socket.

        Args:
            msg: The message to send - this could be a Message, or one of the message subtypes.
        """
        msg = msg if isinstance(msg, Message) else Message(msg)
        tag = msg.root.address.tag
        logging.debug("Tx ctrl->%s: %r", tag, msg)
        pub_message = f"{tag} {msg.model_dump_json()}"
        self.zmq_pub.send_string(pub_message)

    def setup_zmq(self, app, pub_port: int, pull_port: int) -> None:
        """
        Sets up ZeroMQ PUB and PULL sockets and binds them to the specified ports.

        Args:
            app: FastAPI application instance
            pub_port (int): Port number for the PUB socket
            pull_port (int): Port number for the PULL socket
        """
        self.zmq_pub = self.zmq_ctx.socket(zmq.PUB)
        self.zmq_pub.bind(f"tcp://*:{pub_port}")
        self.zmq_pull = self.zmq_ctx.socket(zmq.PULL)
        self.zmq_pull.bind(f"tcp://*:{pull_port}")
        app.state.zmq_ctx = self.zmq_ctx
        app.state.zmq_pub = self.zmq_pub
        app.state.zmq_pull = self.zmq_pull

    def teardown_zmq(self, app) -> None:
        """
        Tears down ZeroMQ sockets and context.

        Args:
            app: FastAPI application instance
        """
        if hasattr(self, "zmq_pub") and self.zmq_pub:
            self.zmq_pub.close()
        if hasattr(self, "zmq_pull") and self.zmq_pull:
            self.zmq_pull.close()
        if hasattr(self, "zmq_ctx") and self.zmq_ctx:
            self.zmq_ctx.term()
        app.state.zmq_ctx = None
        app.state.zmq_pub = None
        app.state.zmq_pull = None


worker_ctrl = ControllerComms()

#######################################################################################################################
# End of file
#######################################################################################################################
