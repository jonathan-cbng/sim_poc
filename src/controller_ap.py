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
                case _:
                    logging.warning(f"Unknown event type: {event}")

    def handle_ap_connected(self, msg):
        try:
            net_idx = int(msg["net"])
            hub_idx = int(msg["hub"])
            ap_idx = int(msg["ap"])
        except (KeyError, ValueError, TypeError) as e:
            logging.warning(f"ap_connected event missing or invalid net/hub/ap fields: {msg} ({e})")
            return
        try:
            ap = nms.get_network(net_idx).get_hub(hub_idx).get_ap(ap_idx)
            ap.state = APState.CONNECTED
            logging.info(f"AP connected: net={net_idx}, hub={hub_idx}, ap={ap_idx}")
        except Exception as e:
            logging.warning(f"Could not mark AP as connected for net={net_idx}, hub={hub_idx}, ap={ap_idx}: {e}")

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
