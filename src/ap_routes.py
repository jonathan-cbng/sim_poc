from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from src.models import AP, RT, APCreateRequest, Message

# In-memory storage for APs and RTs
aps: dict[int, AP] = {}
ap_router = APIRouter(prefix="/ap", tags=["ap"])


@ap_router.post("/", status_code=HTTP_201_CREATED)
def create_ap(req: APCreateRequest) -> int:
    """
    Create & start an AP (optionally with initial RTs)
    """
    if req.ap_id < 0:
        try:
            req.ap_id = max(aps.keys()) + 1
        except ValueError:  # if aps is empty
            req.ap_id = 0
    elif req.ap_id in aps:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="AP already exists")
    rts = [RT(id=i, heartbeat_seconds=req.heartbeat_seconds) for i in range(req.num_rts)]
    new_ap = AP(id=req.ap_id, heartbeat_seconds=req.heartbeat_seconds, rts=rts)

    aps[req.ap_id] = new_ap
    return new_ap.id


@ap_router.get("/")
def list_aps() -> dict[int, AP]:
    """
    List all APs
    """
    return aps


@ap_router.get("/{ap_id}")
def get_ap(ap_id: int) -> AP:
    """
    Get status for a single AP
    """
    ap = aps.get(ap_id)
    if not ap:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="AP not found")
    return ap


# Endpoint: Stop and remove an AP and all underlying RTs
@ap_router.delete("/{ap_id}")
def delete_ap(ap_id: int) -> Message:
    """
    Stop and remove an AP and all underlying RTs
    """
    if ap_id not in aps:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="AP not found")
    del aps[ap_id]
    return Message(message=f"AP {ap_id} deleted")
