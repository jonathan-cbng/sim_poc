import logging

from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from src.manager_hub import HubManager
from src.manager_network import nms
from src.models_api import HubCreateRequest, Result

hub_router = APIRouter(prefix="/network/{network_idx}/hub", tags=["Hub Management"])


@hub_router.post("/", status_code=HTTP_201_CREATED)
async def create_hub(network_idx: int, req: HubCreateRequest) -> int:
    """
    Create & start a Hub (optionally with initial APs and RTs)
    """
    network = nms.get_network(network_idx)
    new_id = await network.add_hub(network_idx, req)
    return new_id


@hub_router.get("/")
async def list_hubs(network_idx: int) -> dict[int, HubManager]:
    """
    List all Hubs
    """
    network = nms.get_network(network_idx)
    logging.info("Listing all %d Hubs for network %d", len(network.children), network_idx)
    return network.get_hubs()


@hub_router.get("/{idx}")
async def get_hub(network_idx: int, idx: int) -> HubManager:
    """
    Get status for a single Hub
    """
    network = nms.get_network(network_idx)
    hub = network.get_hub(idx)
    if not hub:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Hub not found")
    return hub


@hub_router.delete("/{idx}")
async def delete_hub(network_idx: int, idx: int) -> Result:
    """
    Stop and remove a Hub and all underlying APs and RTs
    """
    network = nms.get_network(network_idx)
    await network.remove_hub(idx)
    return Result(message=f"Hub {idx} deleted")
