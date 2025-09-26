"""
Test utilities for network and hub creation in test scenarios.

All code conforms to PEP 8 best practices (except line length <= 120 chars).
Type hints are used where possible. See project template for conventions.
"""

#######################################################################################################################
# Imports
#######################################################################################################################

from starlette.status import HTTP_201_CREATED

from src.config import settings
from src.controller.ctrl_api import HubCreateRequest, NetworkCreateRequest, NetworkRead
from src.controller.worker_ctrl import simulator
from src.worker.worker_api import Address, HubConnectInd

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
    empty_net = await create_empty_net(test_client, httpx_mock)

    httpx_mock.add_response(method="POST", url=f"{settings.NBAPI_URL}/api/v1/node/hub/{TEST_NETWORK_CSNI}_N00H00")

    req = HubCreateRequest(
        num_aps=0,
        ap_heartbeat_seconds=0,
        num_rts_per_ap=0,
        rt_heartbeat_seconds=30,
    )
    # Now we can create the network.
    resp = test_client.post("/network/", json=req.model_dump())

    # Each hub needs to connect to the controller before we create the network
    msg = HubConnectInd(address=Address(net=empty_net.net, hub=0))
    worker = mock_worker(Address(net=empty_net.net, hub=0))
    await worker.send_msg(msg)
    await simulator.children[0].children[0].children[0]._connected_event.wait()
    resp = test_client.post(f"/network/{empty_net.net}/hub", json=req.model_dump())

    assert resp.status_code == HTTP_201_CREATED
    result = NetworkRead.model_validate_json(resp.json())

    return result.address


#######################################################################################################################
# End of file
#######################################################################################################################
