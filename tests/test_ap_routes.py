"""
Tests for AP routes.

This module contains asynchronous pytest test functions for the Access Point (AP) REST API endpoints in the network
controller. The tests cover creating, listing, retrieving, and deleting APs, as well as handling error cases.

"""

# ruff: noqa: PLR2004
#######################################################################################################################
# Imports
#######################################################################################################################
import asyncio
import logging

from starlette.status import HTTP_200_OK, HTTP_202_ACCEPTED, HTTP_404_NOT_FOUND
from tests.utils import create_empty_ap, create_empty_hub

from src.controller.ctrl_api import APCreateRequest, APRead, APState
from src.controller.managers import APManager
from src.controller.worker_ctrl import simulator
from src.worker.worker_api import APRegisterRsp, MessageTypes

#######################################################################################################################
# Globals
#######################################################################################################################

#######################################################################################################################
# Test Bodies
#######################################################################################################################


async def test_create_ap(client, httpx_mock, get_worker_mock):
    """Test creating and starting an AP (optionally with initial RTs).

    Args:
        client: Test client fixture.
        httpx_mock: HTTPX mock fixture.
        get_worker_mock: Worker mock fixture.
    """
    hub_address = await create_empty_hub(client, httpx_mock, get_worker_mock)
    mock_worker = get_worker_mock(hub_address)
    resp = client.post(
        f"/network/{hub_address.net}/hub/{hub_address.hub}/ap/",
        json=APCreateRequest(num_rts=0, heartbeat_seconds=10, rt_heartbeat_seconds=10).model_dump(),
    )
    assert resp.status_code == HTTP_202_ACCEPTED, resp.json()
    ap_resp = APRead.model_validate(resp.json())
    ap_addr = ap_resp.address
    ap = simulator.get_node(ap_addr)
    assert isinstance(ap, APManager)
    msg = await mock_worker.recv_msg()
    assert msg.msg_type == MessageTypes.AP_REGISTER_REQ
    assert msg.address == ap_addr
    reg_resp = APRegisterRsp(success=True, address=ap_addr, registered_at="")
    await mock_worker.send_msg(reg_resp)
    while ap.state != APState.REGISTERED:
        logging.info("Waiting for AP state to become REGISTERED")
        await asyncio.sleep(0.01)


async def test_list_aps(client, httpx_mock, get_worker_mock):
    """Test listing all APs for a hub.

    Args:
        client: Test client fixture.
        httpx_mock: HTTPX mock fixture.
        get_worker_mock: Worker mock fixture.
    """
    hub_addr = await create_empty_hub(client, httpx_mock, get_worker_mock)
    ap1_addr = await create_empty_ap(client, httpx_mock, get_worker_mock, hub_addr)
    ap2_addr = await create_empty_ap(client, httpx_mock, get_worker_mock, hub_addr)
    resp = client.get(f"/network/{ap1_addr.net}/hub/{ap1_addr.hub}/ap/")
    assert resp.status_code == HTTP_200_OK, resp.json()
    aps = resp.json()
    aps = {APRead.model_validate(v).address for k, v in aps.items()}
    assert aps == {ap1_addr, ap2_addr}
    assert len(aps) == 2


async def test_get_ap(client, httpx_mock, get_worker_mock):
    """Test getting status for a single AP.

    Args:
        client: Test client fixture.
        httpx_mock: HTTPX mock fixture.
        get_worker_mock: Worker mock fixture.
    """
    hub_addr = await create_empty_hub(client, httpx_mock, get_worker_mock)
    ap_addr = await create_empty_ap(client, httpx_mock, get_worker_mock, hub_addr)
    resp = client.get(f"/network/{ap_addr.net}/hub/{ap_addr.hub}/ap/{ap_addr.ap}")
    assert resp.status_code == HTTP_200_OK, resp.json()
    ap = resp.json()
    assert ap["address"]["ap"] == ap_addr.ap


async def test_delete_ap(client, httpx_mock, get_worker_mock):
    """Test deleting an AP and confirming it is gone.

    Args:
        client: Test client fixture.
        httpx_mock: HTTPX mock fixture.
        get_worker_mock: Worker mock fixture.
    """
    hub_addr = await create_empty_hub(client, httpx_mock, get_worker_mock)
    ap_addr = await create_empty_ap(client, httpx_mock, get_worker_mock, hub_addr)
    del_resp = client.delete(f"/network/{ap_addr.net}/hub/{ap_addr.hub}/ap/{ap_addr.ap}")
    assert del_resp.status_code == HTTP_200_OK, del_resp.json()
    msg = del_resp.json()
    assert f"AP {ap_addr.ap} deleted" in msg["message"]
    get_resp = client.get(f"/network/{ap_addr.net}/hub/{ap_addr.hub}/ap/{ap_addr.ap}")
    assert get_resp.status_code == HTTP_404_NOT_FOUND


async def test_delete_nonexistent_ap(client, httpx_mock, get_worker_mock):
    """Test deleting a non-existent AP returns 404.

    Args:
        client: Test client fixture.
        httpx_mock: HTTPX mock fixture.
        get_worker_mock: Worker mock fixture.
    """
    hub_addr = await create_empty_hub(client, httpx_mock, get_worker_mock)
    resp = client.delete(f"/network/{hub_addr.net}/hub/{hub_addr.hub}/ap/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND
    data = resp.json()
    assert "not found" in data["detail"].lower()


#######################################################################################################################
# End of file
#######################################################################################################################
