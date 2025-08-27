import pytest
import zmq.asyncio
from fastapi.testclient import TestClient

from src.app import get_app
from src.config import settings


@pytest.fixture(scope="session")
def test_app():
    # Optionally, override settings or dependencies here
    yield get_app()


@pytest.fixture(scope="function")
def test_client(test_app):
    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="function")
def zmq_ctx():
    ctx = zmq.asyncio.Context()
    yield ctx
    ctx.term()


@pytest.fixture(scope="function")
async def subscriber(zmq_ctx):
    """
    Connects to the PUB socket as a SUB socket for test to receive published messages.
    """
    sub = zmq_ctx.socket(zmq.asyncio.SUB)
    sub.connect(f"tcp://127.0.0.1:{settings.PUB_PORT}")
    # Subscribe to all topics by default; test can set more specific filters
    sub.setsockopt(zmq.asyncio.SUBSCRIBE, b"")
    yield sub
    sub.close()


@pytest.fixture(scope="function")
async def pusher(zmq_ctx):
    """
    Connects to the PULL socket as a PUSH socket for test to send messages as if from an AP.
    """
    push = zmq_ctx.socket(zmq.asyncio.PUSH)
    push.connect(f"tcp://127.0.0.1:{settings.PULL_PORT}")
    yield push
    push.close()
