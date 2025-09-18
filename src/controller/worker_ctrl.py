import logging

import zmq
import zmq.asyncio

from src.controller.managers import APManager, HubManager, NodeState, nms
from src.worker.worker_api import APRegisterInd, HubConnectInd, Message, MessageTypes


class WorkerCtrl:
    """Controller for managing communication with worker processes via ZeroMQ."""

    zmq_ctx: zmq.asyncio.Context = None
    zmq_pub: zmq.asyncio.Socket = None
    zmq_pull: zmq.asyncio.Socket = None

    def handle_hub_connect_ind(self, msg: HubConnectInd):
        hub: HubManager = nms.get_node(msg.address)
        hub.on_connect_ind(msg)

    def handle_ap_register_ind(self, msg: APRegisterInd):
        ap = msg.address.get_ap(nms)
        logging.info(f"AP registered: {msg.address}")
        ap.state = NodeState.REGISTERED

    async def listener(self):
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

    def send_to_ap(self, ap: APManager, msg):
        logging.debug("Tx ctrl->%s: %r", ap._tag, msg)
        msg = msg if isinstance(msg, Message) else Message(msg)
        pub_message = f"{ap._tag} {msg.model_dump_json()}"
        self.zmq_pub.send_string(pub_message)

    def setup_zmq(self, app, pub_port, pull_port):
        """
        Sets up ZeroMQ PUB and PULL sockets and binds them to the specified ports.

        :param app: FastAPI application instance
        :param pub_port: Port number for the PUB socket
        :param pull_port: Port number for the PULL socket
        :return: Tuple containing the PUB and PULL sockets
        """
        ctx = zmq.asyncio.Context()
        pub = ctx.socket(zmq.PUB)
        pub.bind(f"tcp://*:{pub_port}")
        pull = ctx.socket(zmq.PULL)
        pull.bind(f"tcp://*:{pull_port}")
        self.zmq_ctx = ctx
        self.zmq_pub = pub
        self.zmq_pull = pull

        return pub, pull

    def teardown_zmq(self, app):
        """
        Closes the PUB and PULL sockets and terminates the context.
        :param app: FastAPI application instance
        """
        if self.zmq_pub:
            self.zmq_pub.close()
            self.zmq_pub = None
        if self.zmq_pull:
            self.zmq_pull.close()
            self.zmq_pull = None
        if self.zmq_ctx:
            self.zmq_ctx.term()
            self.zmq_ctx = None


worker_ctrl = WorkerCtrl()
