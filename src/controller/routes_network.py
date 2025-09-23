"""
Network Management API routes.
"""

#######################################################################################################################
# Imports
#######################################################################################################################
import logging
from typing import Annotated

from fastapi import APIRouter, Body, Path
from starlette.status import HTTP_201_CREATED

from src.controller.ctrl_api import NetworkCreateRequest, NetworkRead, Result
from src.controller.worker_ctrl import simulator

#######################################################################################################################
# Globals
#######################################################################################################################
network_router = APIRouter(prefix="/network", tags=["Network Management"])

#######################################################################################################################
# Body
#######################################################################################################################


@network_router.post("/", status_code=HTTP_201_CREATED)
async def create_network(
    req: Annotated[NetworkCreateRequest, Body(description="Network creation request")],
) -> NetworkRead:
    """
    Create a Network (optionally with initial Hubs, APs and RTs).

    Once nodes are created, they will start sending heartbeats to the controller.

    Args:
        req (NetworkCreateRequest): Network creation request body.

    Returns:
        addr: The address of the newly created Network.
    """
    net_mgr = await simulator.add_network(req)
    net_mgr.start_heartbeats()
    logging.info(f"Created Network {net_mgr.address}")
    return net_mgr


@network_router.get("/")
async def list_networks() -> dict[int, NetworkRead]:
    """
    List all Networks.

    Returns:
        dict[int, NetworkManager]: Dictionary of NetworkManagers keyed by Network ID.
    """
    logging.info(f"Listing all {len(simulator.children)} Networks")
    # result = {idx: NetworkRead.model_validate(net) for idx, net in simulator.children.items()}
    return simulator.children


@network_router.get("/{idx}")
async def get_network(idx: Annotated[int, Path(description="Network index")]) -> NetworkRead:
    """
    Get status for a single Network.

    Args:
        idx (int): Index of the Network.

    Returns:
        NetworkManager: The NetworkManager instance.
    """
    network = simulator.get_network(idx)
    return network


@network_router.delete("/{idx}")
async def delete_network(idx: Annotated[int, Path(description="Network index")]) -> Result:
    """
    Stop and remove a Network and all underlying Hubs, APs, and RTs.

    Args:
        idx (int): Index of the Network.

    Returns:
        Result: Result message.
    """
    await simulator.remove_network(idx)
    logging.info(f"Deleted Network {idx}")
    return Result(message=f"Network {idx} deleted")


#######################################################################################################################
# End of file
#######################################################################################################################
