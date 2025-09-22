import logging

import zmq
import zmq.asyncio

from src.worker.api_types import Message, MessageTypes


class ControllerComms:
    """
    Class to manage communication between the controller and worker nodes using ZeroMQ. This class
    sits on the controller side and uses a PUB socket to send commands to workers and a PULL socket
    to receive status updates from workers.
    """

    simulator = None

    async def listener(self, simulator) -> None:
        """
        Listens for incoming messages on the PULL socket and processes them.

        simulator: The SimulatorManager instance to route messages to the correct node.
        """
        while True:
            msg_bytes = await self.zmq_pull.recv()
            tag, msg_bytes = msg_bytes.split(b" ", 1)
            try:
                msg = Message.model_validate_json(msg_bytes)
                msg = msg.root  # This is the actual message inside the wrapper.
                logging.debug("Rx %s->ctrl: %r", str(tag), msg)  # All messages from a worker have an ap_address
                address = msg.address
                node = simulator.get_node(address)
            except Exception as e:
                logging.warning(f"Received non-JSON message: {msg_bytes!r} ({e})")
                continue
            match msg.msg_type:
                case MessageTypes.HUB_CONNECT_IND:
                    node.on_connect_ind(msg)
                case MessageTypes.AP_REGISTER_IND:
                    node.on_register(msg)
                case _:
                    logging.warning(f"Unknown event type: {msg.msg_type}")

    def send(self, msg) -> None:
        """
        Send a message to an AP via the PUB socket.

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


worker_ctrl = ControllerComms()  # Singleton instance of the simulator manager - this is the top-level data structure
