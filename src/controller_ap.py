import json
import logging

import zmq.asyncio

from src.common import APState
from src.manager_network import nms


class APController:
    zmq_ctx: zmq.asyncio.Context = None
    zmq_pub: zmq.asyncio.Socket = None
    zmq_pull: zmq.asyncio.Socket = None

    async def listener(self):
        """
        Listens for incoming messages on the PULL socket and processes them.
        """
        while True:
            msg_bytes = await self.zmq_pull.recv()
            try:
                msg = json.loads(msg_bytes)
            except Exception as e:
                logging.warning(f"Received non-JSON message: {msg_bytes!r} ({e})")
                continue
            event = msg.get("event")
            match event:
                case "ap_connected":
                    self.handle_ap_connected(msg)
                case "ap_registered":
                    self.handle_ap_registered(msg)
                case _:
                    logging.warning(f"Unknown event type: {event}")

    @staticmethod
    def get_ap_from_msg(msg):
        try:
            net_idx = int(msg["net"])
            hub_idx = int(msg["hub"])
            ap_idx = int(msg["ap"])
            ap = nms.get_network(net_idx).get_hub(hub_idx).get_ap(ap_idx)
            return ap, net_idx, hub_idx, ap_idx
        except Exception as e:
            logging.warning(f"Message missing or invalid net/hub/ap fields: {msg} ({e})")
            return None

    def handle_ap_connected(self, msg):
        ap, net_idx, hub_idx, ap_idx = self.get_ap_from_msg(msg)
        ap.state = APState.CONNECTED
        logging.info(f"AP connected: net={net_idx}, hub={hub_idx}, ap={ap_idx}")
        # Send register request to AP via PUB socket
        register_msg = json.dumps({"event": "register_ap_to_nms"})
        pub_message = f"{ap._tag} {register_msg}"
        self.zmq_pub.send_string(pub_message)
        logging.info(f"Sent register_ap_to_nms to {ap._tag}: {register_msg}")

    def handle_ap_registered(self, msg):
        ap, net_idx, hub_idx, ap_idx = self.get_ap_from_msg(msg)
        logging.info(f"AP registered: net={net_idx}, hub={hub_idx}, ap={ap_idx}")
        ap.state = APState.REGISTERED

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
