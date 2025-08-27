from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from src.ap_controller import ap_ctrl
from src.models import AP, APCreateRequest, Message

ap_router = APIRouter(prefix="/ap", tags=["ap"])
aps: dict[int, AP] = {}


@ap_router.post("/", status_code=HTTP_201_CREATED)
async def create_ap(req: APCreateRequest) -> int:
    """
    Create & start an AP (optionally with initial RTs)
    """
    new_id = await ap_ctrl.add_ap(req)
    return new_id


@ap_router.get("/")
async def list_aps() -> dict[int, AP]:
    """
    List all APs
    """
    return ap_ctrl.aps


@ap_router.get("/{index}")
async def get_ap(index: int) -> AP:
    """
    Get status for a single AP
    """
    ap = ap_ctrl.aps.get(index)
    if not ap:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="AP not found")
    return ap


# Endpoint: Stop and remove an AP and all underlying RTs
@ap_router.delete("/{index}")
async def delete_ap(index: int) -> Message:
    """
    Stop and remove an AP and all underlying RTs
    """
    await ap_ctrl.remove_ap(index)
    return Message(message=f"AP {index} deleted")
