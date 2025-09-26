"""
Test utilities for network and hub creation in test scenarios.

All code conforms to PEP 8 best practices (except line length <= 120 chars).
Type hints are used where possible. See project template for conventions.
"""


#######################################################################################################################
# Imports
#######################################################################################################################

import asyncio
import logging

from starlette.status import HTTP_201_CREATED, HTTP_202_ACCEPTED

from src.config import settings
from src.controller.ctrl_api import (
    APCreateRequest,
    APRead,
    APState,
    HubCreateRequest,
    HubRead,
    HubState,
    NetworkCreateRequest,
    NetworkRead,
)
from src.controller.managers import APManager
from src.controller.worker_ctrl import simulator
from src.worker.worker_api import Address, APRegisterRsp, HubConnectInd, MessageTypes

#######################################################################################################################
# Globals
#######################################################################################################################

TEST_NETWORK_CSNI = "test-network-csni"
NUM_HUBS = 1
NUM_APS_PER_HUB = 2
NUM_RTS_PER_AP = 2

#######################################################################################################################
# Body
#######################################################################################################################


def create_empty_net(test_client, httpx_mock) -> Address:
    """Utility function to create a mini network with the NMS API mocked out. No hubs, APs, or RTs.

    Args:
        test_client: The test client fixture for making HTTP requests.
        httpx_mock: The HTTPX mock fixture for mocking external requests.

    Returns:
        Address: The address of the created network.
    Note:
        httpx_mock is function-scoped and does not require manual release. Responses are cleared at the end for safety.
    """
    req = NetworkCreateRequest(
        hubs=0,
        aps_per_hub=0,
        ap_heartbeat_seconds=30,
        rts_per_ap=0,
        rt_heartbeat_seconds=30,
    )

    # Mock the NMS add network API call
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.NBAPI_URL}/api/v1/network/csi/{req.csi}",
        json={"csni": TEST_NETWORK_CSNI},
    )

    # Now we can create the network.
    resp = test_client.post("/network/", json=req.model_dump())
    assert resp.status_code == HTTP_201_CREATED
    result = NetworkRead.model_validate(resp.json())
    assert result.csni == TEST_NETWORK_CSNI

    return result.address


async def create_empty_hub(test_client, httpx_mock, mock_worker) -> Address:
    """Utility function to create a mini network with a single hub, no APs or RTs.

    Args:
        test_client: The test client fixture for making HTTP requests.
        httpx_mock: The HTTPX mock fixture for mocking external requests.
        mock_worker: The mock worker fixture for simulating worker behavior.

    Returns:
        Address: The address of the created hub.
    Note:
        httpx_mock is function-scoped and does not require manual release. Responses are cleared at the end for safety.
    """
    # Now mock the hub registration calls
    empty_net = create_empty_net(test_client, httpx_mock)

    httpx_mock.add_response(method="POST", url=f"{settings.NBAPI_URL}/api/v1/node/hub/{TEST_NETWORK_CSNI}_N00H00")

    req = HubCreateRequest(
        num_aps=0,
        ap_heartbeat_seconds=0,
        num_rts_per_ap=0,
        rt_heartbeat_seconds=30,
    )
    # Now we can create the network.
    resp = test_client.post(f"/network/{empty_net.net}/hub/", json=req.model_dump())
    resp.raise_for_status()
    assert resp.status_code == HTTP_201_CREATED
    hub_info = HubRead.model_validate(resp.json())
    hub_address = hub_info.address
    hub_mgr = simulator.get_network(hub_address.net).get_hub(hub_address.hub)
    # Each hub needs to connect to the controller before we create the network
    worker = mock_worker(hub_info.address)

    # Send the connect indication and wait for the hub to be marked as connected. This confirms that the mocked
    # worker is working and the hub is fully created.

    await worker.send_msg(HubConnectInd(address=hub_address))
    assert hub_mgr.state == HubState.REGISTERED

    return hub_info.address


async def create_empty_ap(client, httpx_mock, get_worker_mock, hub_address) -> Address:
    """Utility function to create an AP with no RTs under a hub (creates hub if not provided).

    Args:
        client: The test client fixture for making HTTP requests.
        httpx_mock: The HTTPX mock fixture for mocking external requests.
        get_worker_mock: The mock worker fixture for simulating worker behavior.
        hub_address: Optionally, the address of an existing hub. If None, creates an empty hub.

    Returns:
        Tuple: (ap_address, ap_manager, mock_worker)
    """

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

    # We expect the controller to have sent a register request to the worker
    msg = await mock_worker.recv_msg()
    assert msg.msg_type == MessageTypes.AP_REGISTER_REQ
    assert msg.address == ap_addr
    resp_msg = APRegisterRsp(success=True, address=ap_addr, registered_at="")
    await mock_worker.send_msg(resp_msg)

    # Spin-wait for AP to become REGISTERED - test will timeout if it doesn't
    async with asyncio.timeout(1):  # 5 seconds timeout
        while ap.state != APState.REGISTERED:
            logging.info("Waiting for AP state to become REGISTERED")
            await asyncio.sleep(0.01)

    return ap_addr


#######################################################################################################################
# End of file
#######################################################################################################################
