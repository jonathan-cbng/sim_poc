import logging

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.controller.app import get_app
from src.controller.managers import HubManager
from src.controller.worker_ctrl import simulator
from src.worker.comms import WorkerComms

TEST_NETWORK_CSNI = "test-network-csni"
NUM_HUBS = 1
NUM_APS_PER_HUB = 2
NUM_RTS_PER_AP = 2


@pytest.fixture(scope="session")
def test_app():
    # Optionally, override settings or dependencies here
    yield get_app()


@pytest.fixture(scope="function")
def test_client(test_app):
    with TestClient(test_app) as client:
        yield client


@pytest.fixture
def mock_worker(monkeypatch):
    """
    Automatically mock out the worker start/stop methods for all tests. This prevente any actual worker processes
    from being started.

    Returns a helper function to create a mock WorkerComms instance for a given address.
    """

    async def mock_start(hub_mgr):
        logging.info(f"Worker start requested {hub_mgr.address})")

    def mock_stop(hub_mgr):
        logging.info(f"Worker stop requested {hub_mgr.address})")

    monkeypatch.setattr(HubManager, "start_worker", mock_start)
    monkeypatch.setattr(HubManager, "stop_worker", mock_stop)

    def mock_worker_comms(address) -> WorkerComms:
        """
        This is not a fixture, just a helper function to create a mock WorkerComms instance for a given address.
        """
        return WorkerComms(address, f"tcp://127.0.0.1:{settings.PULL_PORT}", f"tcp://127.0.0.1:{settings.PUB_PORT}")

    yield mock_worker_comms


@pytest.fixture(autouse=True)
def reset_ctrls():
    simulator.children.clear()
