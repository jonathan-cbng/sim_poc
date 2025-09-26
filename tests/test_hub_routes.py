"""
Test suite for hub-related API endpoints.

This module contains tests for creating, retrieving, and deleting hubs via the API.
All tests conform to PEP 8 (except line length up to 120) and use Google-style docstrings.
"""

#######################################################################################################################
# Imports
#######################################################################################################################
import pytest
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from tests.utils import TEST_NETWORK_CSNI, create_empty_hub, create_empty_net

from src.config import settings
from src.controller.ctrl_api import HubCreateRequest, HubRead, HubState
from src.worker.worker_api import Address

#######################################################################################################################
# Globals
#######################################################################################################################

#######################################################################################################################
# Body
#######################################################################################################################


async def test_create_hub_minimal(client, httpx_mock, get_worker_mock) -> None:
    """Test creating a minimal hub.

    Args:
        test_client: The test client fixture.
        httpx_mock: The HTTPX mock fixture.
        mock_worker: The mock worker fixture.
    """
    hub = await create_empty_hub(client, httpx_mock, get_worker_mock)
    assert hub == Address(net=0, hub=0)


async def test_get_hub(client, httpx_mock, get_worker_mock) -> None:
    """Test retrieving a single hub.

    Args:
        test_client: The test client fixture.
        httpx_mock: The HTTPX mock fixture.
        mock_worker: The mock worker fixture.
    """
    hub_address = await create_empty_hub(client, httpx_mock, get_worker_mock)
    resp = client.get(f"/network/{hub_address.net}/hub/{hub_address.hub}")
    assert resp.status_code == HTTP_200_OK, resp.json()
    resp = HubRead.model_validate(resp.json())
    assert resp.address == hub_address
    assert resp.state == HubState.REGISTERED


def test_get_nonexistent_hub(client, httpx_mock) -> None:
    """Test retrieving a non-existent hub returns 404.

    Args:
        test_client: The test client fixture.
        httpx_mock: The HTTPX mock fixture.
    """
    netw_addr = create_empty_net(client, httpx_mock)
    resp = client.get(f"/network/{netw_addr.net}/hub/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND
    data = resp.json()
    assert "not found" in data["detail"].lower()


async def test_delete_hub(client, httpx_mock, get_worker_mock) -> None:
    """Test deleting a hub and confirming it is removed.

    Args:
        test_client: The test client fixture.
        httpx_mock: The HTTPX mock fixture.
        mock_worker: The mock worker fixture.
    """
    hub_address = await create_empty_hub(client, httpx_mock, get_worker_mock)
    del_resp = client.delete(f"/network/{hub_address.net}/hub/{hub_address.hub}")
    assert del_resp.status_code == HTTP_200_OK
    msg = del_resp.json()
    assert f"Hub {hub_address.hub} deleted" in msg["message"]
    # Confirm hub is gone
    get_resp = client.get(f"/network/{hub_address.net}/hub/{hub_address.hub}")
    assert get_resp.status_code == HTTP_404_NOT_FOUND


def test_delete_nonexistent_hub(client, httpx_mock, get_worker_mock) -> None:
    """Test deleting a non-existent hub returns 404.

    Args:
        test_client: The test client fixture.
        httpx_mock: The HTTPX mock fixture.
        mock_worker: The mock worker fixture.
    """
    network = create_empty_net(client, httpx_mock)
    resp = client.delete(f"/network/{network.net}/hub/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND
    data = resp.json()
    assert "not found" in data["detail"].lower()


async def test_list_hubs(client, httpx_mock, get_worker_mock) -> None:
    """Test listing multiple hubs.

    Args:
        test_client: The test client fixture.
        httpx_mock: The HTTPX mock fixture.
        mock_worker: The mock worker fixture.
    """
    await create_empty_hub(client, httpx_mock, get_worker_mock)

    httpx_mock.add_response(method="POST", url=f"{settings.NBAPI_URL}/api/v1/node/hub/{TEST_NETWORK_CSNI}_N00H01")

    req = HubCreateRequest(
        num_aps=0,
        ap_heartbeat_seconds=0,
        num_rts_per_ap=0,
        rt_heartbeat_seconds=30,
    )
    # Now we can create the network.
    resp = client.post("/network/0/hub/", json=req.model_dump())
    resp.raise_for_status()

    resp = client.get("/network/0/hub/")
    assert resp.status_code == HTTP_200_OK
    hubs = resp.json()
    assert isinstance(hubs, dict)
    assert len(hubs) >= 2  # noqa: PLR2004


@pytest.mark.skip(reason="Not implemented yet")
def test_delete_hub_removes_aps(client, httpx_mock, get_worker_mock) -> None:
    """Test deleting a hub also removes its APs (not implemented).

    Args:
        test_client: The test client fixture.
        httpx_mock: The HTTPX mock fixture.
        mock_worker: The mock worker fixture.
    """
    # TODO: Create a hub with APs, delete the hub, verify APs are also deleted
    raise NotImplementedError


@pytest.mark.skip(reason="Not implemented yet")
def test_create_hub_with_aps_rts(client, httpx_mock, get_worker_mock) -> None:
    """Test creating a hub with APs and RTs (not implemented).

    Args:
        test_client: The test client fixture.
        httpx_mock: The HTTPX mock fixture.
        mock_worker: The mock worker fixture.
    """
    # TODO: Create a hub with APs and RTs, verify they are created correctly
    raise NotImplementedError


#######################################################################################################################
# End of file
#######################################################################################################################
