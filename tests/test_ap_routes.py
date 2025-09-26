import asyncio
import logging

import pytest
from starlette.status import HTTP_202_ACCEPTED
from tests.utils import create_empty_hub

from src.controller.ctrl_api import APCreateRequest, APRead, APState
from src.controller.managers import APManager
from src.controller.worker_ctrl import simulator
from src.worker.worker_api import APRegisterRsp, MessageTypes


# Test: Create & start an AP (optionally with initial RTs)
@pytest.mark.timeout(1)
async def test_create_ap(client, client_async, httpx_mock, get_worker_mock):
    hub_address = await create_empty_hub(client, httpx_mock, get_worker_mock)
    mock_worker = get_worker_mock(hub_address)

    resp = client.post(
        f"/network/{hub_address.net}/hub/{hub_address.hub}/ap/",
        json=APCreateRequest(num_rts=0).model_dump(),
    )
    assert resp.status_code == HTTP_202_ACCEPTED, resp.json()

    ap_resp = APRead.model_validate(resp.json())
    ap_addr = ap_resp.address
    ap = simulator.get_node(ap_addr)
    assert isinstance(ap, APManager)

    # We expect the controller to have sent a register request to thw worker
    msg = await mock_worker.recv_msg()
    assert msg.msg_type == MessageTypes.AP_REGISTER_REQ
    assert msg.address == ap_addr
    resp = APRegisterRsp(success=True, address=ap_addr, registered_at="")

    await mock_worker.send_msg(resp)

    # Spin-wait for AP to become REGISTERED - test will timeout if it doesn't
    while ap.state != APState.REGISTERED:
        logging.info("Waiting for AP state to become REGISTERED")
        await asyncio.sleep(0.01)


# Disabled for now
# Test: List all APs
# def test_list_aps(client):
#     network_idx = create_network(client)
#     hub_idx = create_hub(client, network_idx)
#     client.post(
#         f"/network/{network_idx}/hub/{hub_idx}/ap/",
#         json={"heartbeat_seconds": 10, "num_rts": 1, "rt_heartbeat_seconds": 10},
#     )
#     client.post(
#         f"/network/{network_idx}/hub/{hub_idx}/ap/",
#         json={"heartbeat_seconds": 20, "num_rts": 2, "rt_heartbeat_seconds": 10},
#     )
#     resp = client.get(f"/network/{network_idx}/hub/{hub_idx}/ap/")
#     assert resp.status_code == HTTP_200_OK
#     aps = resp.json()
#     assert isinstance(aps, dict)
#     assert len(aps) >= 2  # noqa: PLR2004
#
#
# # Test: Get status for a single AP
# def test_get_ap(client):
#     network_idx = create_network(client)
#     hub_idx = create_hub(client, network_idx)
#     num_rts = 3
#     hb_seconds = 15
#     create_resp = client.post(
#         f"/network/{network_idx}/hub/{hub_idx}/ap/",
#         json={"heartbeat_seconds": hb_seconds, "num_rts": num_rts, "rt_heartbeat_seconds": 10},
#     )
#     ap_id = create_resp.json()
#     resp = client.get(f"/network/{network_idx}/hub/{hub_idx}/ap/{ap_id}")
#     assert resp.status_code == HTTP_200_OK
#     ap = resp.json()
#     assert ap["index"] == ap_id
#     assert ap["heartbeat_seconds"] == hb_seconds
#     assert len(ap["children"]) == num_rts
#
#
# # Test: Delete an AP
# def test_delete_ap(client):
#     network_idx = create_network(client)
#     hub_idx = create_hub(client, network_idx)
#     create_resp = client.post(
#         f"/network/{network_idx}/hub/{hub_idx}/ap/",
#         json={"heartbeat_seconds": 10, "num_rts": 1, "rt_heartbeat_seconds": 10},
#     )
#     ap_id = create_resp.json()
#     del_resp = client.delete(f"/network/{network_idx}/hub/{hub_idx}/ap/{ap_id}")
#     assert del_resp.status_code == HTTP_200_OK
#     msg = del_resp.json()
#     assert f"AP {ap_id} deleted" in msg["message"]
#     # Confirm AP is gone
#     get_resp = client.get(f"/network/{network_idx}/hub/{hub_idx}/ap/{ap_id}")
#     assert get_resp.status_code == HTTP_404_NOT_FOUND
#
#
# # Test: Delete a non-existent AP
# def test_delete_nonexistent_ap(client):
#     network_idx = create_network(client)
#     hub_idx = create_hub(client, network_idx)
#     resp = client.delete(f"/network/{network_idx}/hub/{hub_idx}/ap/9999")
#     assert resp.status_code == HTTP_404_NOT_FOUND
#     data = resp.json()
#     assert "not found" in data["detail"].lower()
