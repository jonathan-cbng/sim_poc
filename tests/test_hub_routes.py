import pytest
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from tests.utils import create_empty_hub, create_empty_net

from src.controller.ctrl_api import HubRead, HubState
from src.worker.worker_api import Address


async def test_create_hub_minimal(test_client, httpx_mock, mock_worker):
    hub = await create_empty_hub(test_client, httpx_mock, mock_worker)
    assert hub == Address(net=0, hub=0)


# Test: Get a single hub
async def test_get_hub(test_client, httpx_mock, mock_worker):
    hub_address = await create_empty_hub(test_client, httpx_mock, mock_worker)
    resp = test_client.get(f"/network/{hub_address.net}/hub/{hub_address.hub}")
    assert resp.status_code == HTTP_200_OK, resp.json()
    resp = HubRead.model_validate(resp.json())

    assert resp.address == hub_address
    assert resp.state == HubState.REGISTERED


# Test: Get a non-existent hub
def test_get_nonexistent_hub(test_client, httpx_mock):
    netw_addr = create_empty_net(test_client, httpx_mock)
    resp = test_client.get(f"/network/{netw_addr.net}/hub/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND
    data = resp.json()
    assert "not found" in data["detail"].lower()


# Test: Delete a hub
async def test_delete_hub(test_client, httpx_mock, mock_worker):
    hub_address = await create_empty_hub(test_client, httpx_mock, mock_worker)

    del_resp = test_client.delete(f"/network/{hub_address.net}/hub/{hub_address.hub}")
    assert del_resp.status_code == HTTP_200_OK
    msg = del_resp.json()
    assert f"Hub {hub_address.hub} deleted" in msg["message"]
    # Confirm hub is gone
    get_resp = test_client.get(f"/network/{hub_address.net}/hub/{hub_address.hub}")
    assert get_resp.status_code == HTTP_404_NOT_FOUND


# Test: Delete a non-existent hub
def test_delete_nonexistent_hub(test_client, httpx_mock, mock_worker):
    network = create_empty_net(test_client, httpx_mock)
    resp = test_client.delete(f"/network/{network.net}/hub/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND
    data = resp.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.skip(reason="Not implemented yet")
async def test_list_hubs(test_client, httpx_mock, mock_worker):
    # TODO: Create multiple hubs and verify they are all listed
    hub1 = await create_empty_hub(test_client, httpx_mock, mock_worker)

    resp = test_client.get(f"/network/{hub1.net}/hub/")
    assert resp.status_code == HTTP_200_OK
    hubs = resp.json()
    assert isinstance(hubs, dict)
    assert len(hubs) >= 2  # noqa: PLR2004


@pytest.mark.skip(reason="Not implemented yet")
def test_delete_hub_removes_aps(test_client, httpx_mock, mock_worker):
    # TODO: Create a hub with APs, delete the hub, verify APs are also deleted
    raise NotImplementedError


@pytest.mark.skip(reason="Not implemented yet")
def test_create_hub_with_aps_rts(test_client, httpx_mock, mock_worker):
    # TODO: Create a hub with APs and RTs, verify they are created correctly
    raise NotImplementedError
