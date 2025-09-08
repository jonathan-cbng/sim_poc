import logging

import zmq.asyncio

from src.common import AP, APState
from src.manager_network import nms
from src.worker.api import APConnectInd, APRegistered, APRegisterReq, Message


class APController:
    zmq_ctx: zmq.asyncio.Context = None
    zmq_pub: zmq.asyncio.Socket = None
    zmq_pull: zmq.asyncio.Socket = None

    def handle_ap_connected(self, msg: APConnectInd):
        ap = msg.ap_address.get_ap(nms)
        ap.state = APState.CONNECTED
        logging.info(f"AP connected: {msg.ap_address}")
        register_msg = APRegisterReq()
        self.send_to_ap(ap, register_msg)

    def handle_ap_registered(self, msg: APRegistered):
        ap = msg.ap_address.get_ap(nms)
        logging.info(f"AP registered: {msg.ap_address}")
        ap.state = APState.REGISTERED

    async def listener(self):
        """
        Listens for incoming messages on the PULL socket and processes them.
        """
        while True:
            msg_bytes = await self.zmq_pull.recv()
            try:
                msg = Message.model_validate_json(msg_bytes)
                msg = msg.root  # This is the actual message inside the wrapper
                logging.info(f"Decoded message: {msg}")
            except Exception as e:
                logging.warning(f"Received non-JSON message: {msg_bytes!r} ({e})")
                continue
            match msg.msg_type:
                case "ap_connect_ind":
                    self.handle_ap_connected(msg)
                case "ap_register_ind":
                    self.handle_ap_registered(msg)
                case _:
                    logging.warning(f"Unknown event type: {msg.msg_type}")

    def send_to_ap(self, ap: AP, msg):
        msg = msg if isinstance(msg, Message) else Message(msg)
        pub_message = f"{ap._tag} {msg.model_dump_json()}"
        self.zmq_pub.send_string(pub_message)
        logging.info(f"Sent {pub_message}")

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


ap_ctrl = APController()
