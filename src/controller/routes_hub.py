"""
Hub Management API routes.
"""

#######################################################################################################################
# Imports
#######################################################################################################################
import logging
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from src.controller.api import HubCreateRequest, Result
from src.controller.managers import HubManager, nms

#######################################################################################################################
# Globals
#######################################################################################################################
hub_router = APIRouter(prefix="/network/{network_idx}/hub", tags=["Hub Management"])

#######################################################################################################################
# Body
#######################################################################################################################


@hub_router.post("/", status_code=HTTP_201_CREATED)
async def create_hub(
    network_idx: Annotated[int, Path(description="Network index")],
    req: Annotated[HubCreateRequest, Body(description="Hub creation request")],
) -> int:
    """
    Create and start a Hub (optionally with initial APs and RTs).

    Args:
        network_idx (int): Index of the network.
        req (HubCreateRequest): Hub creation request body.

    Returns:
        int: The ID of the newly created Hub.
    """
    network = nms.get_network(network_idx)
    new_id = await network.add_hub(req)
    logging.info(f"Created Hub {new_id} in network {network_idx}")
    return new_id


@hub_router.get("/")
async def list_hubs(
    network_idx: Annotated[int, Path(description="Network index")],
) -> dict[int, HubManager]:
    """
    List all Hubs in a network.

    Args:
        network_idx (int): Index of the network.

    Returns:
        dict[int, HubManager]: Dictionary of HubManagers keyed by Hub ID.
    """
    network = nms.get_network(network_idx)
    logging.info(f"Listing all {len(network.children)} Hubs for network {network_idx}")
    return network.get_hubs()


@hub_router.get("/{idx}")
async def get_hub(
    network_idx: Annotated[int, Path(description="Network index")],
    idx: Annotated[int, Path(description="Hub index")],
) -> HubManager:
    """
    Get status for a single Hub.

    Args:
        network_idx (int): Index of the network.
        idx (int): Index of the Hub.

    Returns:
        HubManager: The HubManager instance.
    """
    network = nms.get_network(network_idx)
    hub = network.get_hub(idx)
    if not hub:
        logging.warning(f"Hub {idx} not found in network {network_idx}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Hub not found")
    return hub


@hub_router.delete("/{idx}")
async def delete_hub(
    network_idx: Annotated[int, Path(description="Network index")],
    idx: Annotated[int, Path(description="Hub index")],
) -> Result:
    """
    Stop and remove a Hub and all underlying APs and RTs.

    Args:
        network_idx (int): Index of the network.
        idx (int): Index of the Hub.

    Returns:
        Result: Result message.
    """
    network = nms.get_network(network_idx)
    await network.remove_hub(idx)
    logging.info(f"Deleted Hub {idx} from network {network_idx}")
    return Result(message=f"Hub {idx} deleted")


#######################################################################################################################
# End of file
#######################################################################################################################
