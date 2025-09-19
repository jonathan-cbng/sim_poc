"""
Worker controller for managing communication with worker processes via ZeroMQ.
"""

#######################################################################################################################
# Imports
#######################################################################################################################
import logging

import zmq
import zmq.asyncio

from src.controller.managers import APManager, HubManager, nms
from src.worker.worker_api import APRegisterInd, HubConnectInd, Message, MessageTypes

#######################################################################################################################
# Globals
#######################################################################################################################
# ...existing code...
#######################################################################################################################
# Body
#######################################################################################################################


class WorkerCtrl:
    """
    Controller for managing communication with worker processes via ZeroMQ.
    """

    zmq_ctx: zmq.asyncio.Context = None
    zmq_pub: zmq.asyncio.Socket = None
    zmq_pull: zmq.asyncio.Socket = None

    def handle_hub_connect_ind(self, msg: HubConnectInd) -> None:
        """
        Handle HubConnectInd message from worker.

        Args:
            msg (HubConnectInd): The hub connect indication message.
        """
        hub: HubManager = nms.get_node(msg.address)
        hub.on_connect_ind(msg)

    def handle_ap_register_ind(self, msg: APRegisterInd) -> None:
        """
        Handle APRegisterInd message from worker.

        Args:
            msg (APRegisterInd): The AP register indication message.
        """
        ap: APManager = nms.get_node(msg.address)
        logging.info(f"AP registered: {msg.address}")
        ap.on_register(msg)

    async def listener(self) -> None:
        """
        Listens for incoming messages on the PULL socket and processes them.
        """
        while True:
            msg_bytes = await self.zmq_pull.recv()
            tag, msg_bytes = msg_bytes.split(b" ", 1)
            try:
                msg = Message.model_validate_json(msg_bytes)
                msg = msg.root  # This is the actual message inside the wrapper.
                logging.debug("Rx %s->ctrl: %r", str(tag), msg)  # All messages from a worker have an ap_address
            except Exception as e:
                logging.warning(f"Received non-JSON message: {msg_bytes!r} ({e})")
                continue
            match msg.msg_type:
                case MessageTypes.HUB_CONNECT_IND:
                    self.handle_hub_connect_ind(msg)
                case MessageTypes.AP_REGISTER_IND:
                    self.handle_ap_register_ind(msg)
                case _:
                    logging.warning(f"Unknown event type: {msg.msg_type}")

    def send_to_ap(self, ap: APManager, msg) -> None:
        """
        Send a message to an AP via the PUB socket.

        Args:
            ap (APManager): The AP manager instance.
            msg: The message to send.
        """
        logging.debug("Tx ctrl->%s: %r", ap._tag, msg)
        msg = msg if isinstance(msg, Message) else Message(msg)
        pub_message = f"{ap._tag} {msg.model_dump_json()}"
        self.zmq_pub.send_string(pub_message)

    def setup_zmq(self, app, pub_port: int, pull_port: int) -> None:
        """
        Sets up ZeroMQ PUB and PULL sockets and binds them to the specified ports.

        Args:
            app: FastAPI application instance
            pub_port (int): Port number for the PUB socket
            pull_port (int): Port number for the PULL socket
        """
        self.zmq_ctx = zmq.asyncio.Context()
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
        if self.zmq_pub:
            self.zmq_pub.close()
        if self.zmq_pull:
            self.zmq_pull.close()
        if self.zmq_ctx:
            self.zmq_ctx.term()
        app.state.zmq_ctx = None
        app.state.zmq_pub = None
        app.state.zmq_pull = None


worker_ctrl = WorkerCtrl()
#######################################################################################################################
# End of file
#######################################################################################################################
