from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from src.controller.api import APCreateRequest, Result
from src.controller.managers import APManager, nms

ap_router = APIRouter(prefix="/network/{network_idx}/hub/{hub_idx}/ap", tags=["AP Management"])


@ap_router.post("/", status_code=HTTP_201_CREATED)
async def create_ap(network_idx: int, hub_idx: int, req: APCreateRequest) -> int:
    network = nms.get_network(network_idx)
    hub = network.get_hub(hub_idx)
    ap_obj = await hub.add_ap(req)
    return ap_obj.index


@ap_router.get("/")
async def list_aps(network_idx: int, hub_idx: int) -> dict[int, APManager]:
    network = nms.get_network(network_idx)
    hub = network.get_hub(hub_idx)
    return hub.children


@ap_router.get("/{idx}")
async def get_ap(network_idx: int, hub_idx: int, idx: int) -> APManager:
    network = nms.get_network(network_idx)
    hub = network.get_hub(hub_idx)
    ap = hub.children.get(idx)
    if not ap:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="AP not found")
    return ap


@ap_router.delete("/{idx}")
async def delete_ap(network_idx: int, hub_idx: int, idx: int) -> Result:
    network = nms.get_network(network_idx)
    hub = network.get_hub(hub_idx)
    await hub.remove_ap(idx)
    return Result(message=f"AP {idx} deleted")
