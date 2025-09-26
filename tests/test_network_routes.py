"""
Tests for network routes.

All code conforms to PEP 8 best practices (except line length <= 120 chars).
Type hints are used where possible. See project template for conventions.
"""

import pytest

#######################################################################################################################
# Imports
#######################################################################################################################
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from tests.utils import create_empty_net

from src.controller.ctrl_api import NetworkRead, NetworkState

#######################################################################################################################
# Globals
#######################################################################################################################

#######################################################################################################################
# Body
#######################################################################################################################


def test_list_networks(test_client, httpx_mock):
    """Test: List all networks.

    Args:
        test_client: The test client fixture for making HTTP requests.
        httpx_mock: The HTTPX mock fixture for mocking external requests.
    """
    create_empty_net(test_client, httpx_mock)
    create_empty_net(test_client, httpx_mock)
    resp = test_client.get("/network/")
    assert resp.status_code == HTTP_200_OK
    networks = resp.json()
    assert len(networks) == 2  # noqa: PLR2004


def test_get_network(test_client, httpx_mock):
    """Test: Get a single network.

    Args:
        test_client: The test client fixture for making HTTP requests.
        httpx_mock: The HTTPX mock fixture for mocking external requests.
    """
    net_address = create_empty_net(test_client, httpx_mock)
    resp = test_client.get(f"/network/{net_address.net}")
    assert resp.status_code == HTTP_200_OK, resp.json()
    result = NetworkRead.model_validate(resp.json())
    assert result.state == NetworkState.REGISTERED


def test_get_nonexistent_network(test_client):
    """Test: Get a non-existent network.

    Args:
        test_client: The test client fixture for making HTTP requests.
    """
    resp = test_client.get("/network/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND, resp.json()
    data = resp.json()
    assert "not found" in data["detail"].lower()


def test_delete_network(test_client, httpx_mock):
    """Test: Delete a network.

    Args:
        test_client: The test client fixture for making HTTP requests.
        httpx_mock: The HTTPX mock fixture for mocking external requests.
    """
    net_address = create_empty_net(test_client, httpx_mock)
    resp = test_client.delete(f"/network/{net_address.net}")
    assert resp.status_code == HTTP_200_OK, resp.json()
    resp = test_client.get(f"/network/{net_address.net}")
    assert resp.status_code == HTTP_404_NOT_FOUND, resp.json()
    data = resp.json()
    assert "not found" in data["detail"].lower()


def test_delete_nonexistent_network(test_client):
    """Test: Delete a non-existent network.

    Args:
        test_client: The test client fixture for making HTTP requests.
    """
    resp = test_client.delete("/network/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND, resp.json()
    data = resp.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.skip(reason="Not implemented yet")
def test_delete_network_removes_children(test_client):
    """Test: Deleting a network removes its APs. Not implemented yet.

    Args:
        test_client: The test client fixture for making HTTP requests.
    """
    # TODO
    raise NotImplementedError


@pytest.mark.skip(reason="Not implemented yet")
def test_create_network_with_aps_rts(test_client):
    """Test: Create a network with APs and RTs. Not implemented yet.

    Args:
        test_client: The test client fixture for making HTTP requests.
    """
    # TODO
    raise NotImplementedError


#######################################################################################################################
# End of file
#######################################################################################################################
