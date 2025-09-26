"""
conftest.py

Test fixtures for the controller FastAPI application and related components.

This module provides pytest fixtures for setting up the FastAPI app, test client, and mocking worker communication
for tests.
"""
#######################################################################################################################
# Imports
#######################################################################################################################

import logging
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.config import settings
from src.controller.app import get_app
from src.controller.managers import HubManager
from src.controller.worker_ctrl import simulator
from src.worker.comms import WorkerComms
from src.worker.worker_api import Address

#######################################################################################################################
# Globals
#######################################################################################################################

TEST_NETWORK_CSNI = "test-network-csni"
NUM_HUBS = 1
NUM_APS_PER_HUB = 2
NUM_RTS_PER_AP = 2

#######################################################################################################################
# Fixtures
#######################################################################################################################


@pytest.fixture
def test_app() -> FastAPI:
    """
    Fixture to provide a new FastAPI app instance for each test.

    Clears the global simulator state before each test to ensure isolation.

    Returns:
        FastAPI: The FastAPI application instance.
    """
    simulator.children.clear()  # simulator is a global singleton, so clear any existing state before each test
    # Optionally, override settings or dependencies here
    return get_app()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """
    Fixture to provide a TestClient for the FastAPI app.

    Args:
        test_app (FastAPI): The FastAPI application instance.

    Returns:
        TestClient: The test client for making HTTP requests to the app.
    """
    with TestClient(test_app) as client:
        yield client


@pytest.fixture
async def client_async(test_app: FastAPI) -> AsyncClient:
    """
    Fixture to provide an asynchronous HTTP client for the FastAPI app.
    Args:
        test_app (FastAPI): The FastAPI application instance.
    Returns:
        AsyncClient: The asynchronous HTTP client for making requests to the app.
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def get_worker_mock(monkeypatch) -> Callable[[Address, Callable], WorkerComms]:
    """
    Fixture to mock out the worker start/stop methods for all tests.

    Prevents any actual worker processes from being started. Returns a helper function to create a mock WorkerComms
    instance for a given address.

    Args:
        monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

    Returns:
        Callable[[str], WorkerComms]: Helper function to create a mock WorkerComms instance for a given address.
    """

    async def mock_start(hub_mgr):
        logging.info(f"Worker start requested {hub_mgr.address})")

    def mock_stop(hub_mgr):
        logging.info(f"Worker stop requested {hub_mgr.address})")

    monkeypatch.setattr(HubManager, "start_worker", mock_start)
    monkeypatch.setattr(HubManager, "stop_worker", mock_stop)

    def mock_worker_comms(address: Address) -> WorkerComms:
        """
        Helper function to create a mock WorkerComms instance for a given address.

        Args:
            address (str): The address for the WorkerComms instance.

        Returns:
            WorkerComms: The mock WorkerComms instance.
        """

        return WorkerComms(address, f"tcp://127.0.0.1:{settings.PULL_PORT}", f"tcp://127.0.0.1:{settings.PUB_PORT}")

    yield mock_worker_comms


#######################################################################################################################
# End of file
#######################################################################################################################
