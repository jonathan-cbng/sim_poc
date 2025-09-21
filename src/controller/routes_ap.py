"""
AP Management API routes.
"""

#######################################################################################################################
# Imports
#######################################################################################################################
import logging
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from src.controller.api import APCreateRequest, Result
from src.controller.managers import APManager
from src.controller.worker_ctrl import simulator
from src.worker.worker_api import Address

#######################################################################################################################
# Globals
#######################################################################################################################
ap_router = APIRouter(prefix="/network/{network_idx}/hub/{hub_idx}/ap", tags=["AP Management"])

#######################################################################################################################
# Body
#######################################################################################################################


@ap_router.post("/", status_code=HTTP_201_CREATED)
async def create_ap(
    network_idx: Annotated[int, Path(description="Network index")],
    hub_idx: Annotated[int, Path(description="Hub index")],
    req: Annotated[APCreateRequest, Body(description="AP creation request")],
) -> int:
    """
    Create and start an AP (optionally with initial RTs).

    Args:
        network_idx (int): Index of the network.
        hub_idx (int): Index of the Hub.
        req (APCreateRequest): AP creation request body.

    Returns:
        int: The ID of the newly created AP.
    """
    address = Address(net=network_idx, hub=hub_idx)
    hub = simulator.get_node(address)
    ap_obj = await hub.add_ap(req)
    logging.info(f"Created AP {ap_obj.index} in hub {hub_idx} (network {network_idx})")
    return ap_obj.index


@ap_router.get("/")
async def list_aps(
    network_idx: Annotated[int, Path(description="Network index")],
    hub_idx: Annotated[int, Path(description="Hub index")],
) -> dict[int, APManager]:
    """
    List all APs in a Hub.

    Args:
        network_idx (int): Index of the network.
        hub_idx (int): Index of the Hub.

    Returns:
        dict[int, APManager]: Dictionary of APManagers keyed by AP ID.
    """
    address = Address(net=network_idx, hub=hub_idx)
    hub = simulator.get_node(address)
    logging.info(f"Listing all {len(hub.children)} APs for hub {hub_idx} (network {network_idx})")
    return hub.children


@ap_router.get("/{idx}")
async def get_ap(
    network_idx: Annotated[int, Path(description="Network index")],
    hub_idx: Annotated[int, Path(description="Hub index")],
    idx: Annotated[int, Path(description="AP index")],
) -> APManager:
    """
    Get status for a single AP.

    Args:
        network_idx (int): Index of the network.
        hub_idx (int): Index of the Hub.
        idx (int): Index of the AP.

    Returns:
        APManager: The APManager instance.
    """
    address = Address(net=network_idx, hub=hub_idx, ap=idx)
    ap = simulator.get_node(address)
    if not ap:
        logging.warning(f"AP {idx} not found in hub {hub_idx} (network {network_idx})")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="AP not found")
    return ap


@ap_router.delete("/{idx}")
async def delete_ap(
    network_idx: Annotated[int, Path(description="Network index")],
    hub_idx: Annotated[int, Path(description="Hub index")],
    idx: Annotated[int, Path(description="AP index")],
) -> Result:
    """
    Stop and remove an AP and all underlying RTs.

    Args:
        network_idx (int): Index of the network.
        hub_idx (int): Index of the Hub.
        idx (int): Index of the AP.

    Returns:
        Result: Result message.
    """
    address = Address(net=network_idx, hub=hub_idx)
    hub = simulator.get_node(address)
    await hub.remove_ap(idx)
    logging.info(f"Deleted AP {idx} from hub {hub_idx} (network {network_idx})")
    return Result(message=f"AP {idx} deleted")


#######################################################################################################################
# End of file
#######################################################################################################################
