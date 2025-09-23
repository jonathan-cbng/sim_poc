"""
Network Management API routes.
"""

#######################################################################################################################
# Imports
#######################################################################################################################
import logging
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from src.controller.api import NetworkCreateRequest, Result
from src.controller.managers import NetworkManager
from src.controller.worker_ctrl import simulator
from src.worker.api_types import Address

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
) -> Address:
    """
    Create and start a Network (optionally with initial Hubs).

    Args:
        req (NetworkCreateRequest): Network creation request body.

    Returns:
        addr: The address of the newly created Network.
    """
    net_mgr = await simulator.add_network(req)
    logging.info(f"Created Network {net_mgr.address}")
    return net_mgr.address


@network_router.get("/")
async def list_networks() -> dict[int, NetworkManager]:
    """
    List all Networks.

    Returns:
        dict[int, NetworkManager]: Dictionary of NetworkManagers keyed by Network ID.
    """
    logging.info(f"Listing all {len(simulator.children)} Networks")
    return simulator.children


@network_router.get("/{idx}")
async def get_network(idx: Annotated[int, Path(description="Network index")]) -> NetworkManager:
    """
    Get status for a single Network.

    Args:
        idx (int): Index of the Network.

    Returns:
        NetworkManager: The NetworkManager instance.
    """
    network = simulator.get_network(idx)
    if not network:
        logging.warning(f"Network {idx} not found")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Network not found")
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
