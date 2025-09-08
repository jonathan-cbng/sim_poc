from fastapi import APIRouter
from starlette.status import HTTP_201_CREATED

from src.api import NetworkCreateRequest, Result
from src.manager_network import NetworkManager, nms

network_router = APIRouter(prefix="/network", tags=["Network Management"])


@network_router.post("/", status_code=HTTP_201_CREATED)
async def create_network(req: NetworkCreateRequest) -> int:
    """
    Create & start an AP (optionally with initial RTs)
    """
    new_id = await nms.add_network(req)
    return new_id


@network_router.get("/")
async def list_networks() -> dict[int, NetworkManager]:
    """
    List all APs
    """
    return nms.children


@network_router.get("/{idx}")
async def get_network(idx: int) -> NetworkManager:
    """
    Get status for a single AP
    """
    return nms.get_network(idx)


# Endpoint: Stop and remove an AP and all underlying RTs
@network_router.delete("/{idx}")
async def delete_network(idx: int) -> Result:
    """
    Stop and remove an AP and all underlying RTs
    """
    await nms.remove_network(idx)
    return Result(message=f"Network {idx} deleted")
