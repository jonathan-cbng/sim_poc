# In-memory storage for APs and RTs
import logging

import zmq.asyncio

from src.models import AP

aps: dict[int, AP] = {}


async def listener(pull):
    """
    Listens for incoming messages on the PULL socket and processes them.
    """
    while True:
        msg = await pull.recv()
        logging.debug("Received message: `%s`", msg)


async def setup_zmq(app, pub_port, pull_port):
    """
    Sets up ZeroMQ PUB and PULL sockets and binds them to the specified ports.
    Stores the context and sockets in the FastAPI app state for later use.
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
    app.state.zmq_ctx = ctx
    app.state.zmq_pub = pub
    app.state.zmq_pull = pull
    return pub, pull
