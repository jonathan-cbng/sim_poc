"""
AP Management API routes.
"""

#######################################################################################################################
# Imports
#######################################################################################################################
import logging
from typing import Annotated

from fastapi import APIRouter, Body, Path
from starlette.status import HTTP_202_ACCEPTED

from src.controller.ctrl_api import APCreateRequest, APRead, Result
from src.controller.worker_ctrl import simulator
from src.worker.worker_api import Address

#######################################################################################################################
# Globals
#######################################################################################################################
ap_router = APIRouter(prefix="/network/{network_idx}/hub/{hub_idx}/ap", tags=["AP Management"])

#######################################################################################################################
# Body
#######################################################################################################################


@ap_router.post("/", status_code=HTTP_202_ACCEPTED)
async def create_ap(
    network_idx: Annotated[int, Path(description="Network index")],
    hub_idx: Annotated[int, Path(description="Hub index")],
    req: Annotated[APCreateRequest, Body(description="AP creation request")],
) -> APRead:
    """
    Create and start an AP (optionally with initial RTs). The AP will attempt to register with the NMS in the
    background. If you need to ensure the AP is registered before proceeding, you should poll the AP status
    until it reaches the REGISTERED state.

    Args:
        network_idx (int): Index of the network.
        hub_idx (int): Index of the Hub.
        req (APCreateRequest): AP creation request body.

    Returns:
        addr: The address of the newly created AP.
    """
    address = Address(net=network_idx, hub=hub_idx)
    hub = simulator.get_node(address)
    ap_obj = await hub.add_ap(req)
    logging.info(f"Created AP {ap_obj.address})")
    return ap_obj


@ap_router.get("/")
async def list_aps(
    network_idx: Annotated[int, Path(description="Network index")],
    hub_idx: Annotated[int, Path(description="Hub index")],
) -> dict[int, APRead]:
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
    logging.info(f"Listing all {len(hub.children)} APs for hub {address}")
    return hub.children


@ap_router.get("/{idx}")
async def get_ap(
    network_idx: Annotated[int, Path(description="Network index")],
    hub_idx: Annotated[int, Path(description="Hub index")],
    idx: Annotated[int, Path(description="AP index")],
) -> APRead:
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
    return simulator.get_node(address)


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
    logging.info(f"Deleted AP {idx} from hub {hub.address}")
    return Result(message=f"AP {idx} deleted")


#######################################################################################################################
# End of file
#######################################################################################################################
