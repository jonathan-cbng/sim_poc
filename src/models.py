from pydantic import BaseModel, Field

from src.config import settings


# Pydantic models
class Node(BaseModel):
    index: int
    str_id: str = ""
    heartbeat_seconds: int


class RT(Node):
    pass


class AP(Node):
    rts: list[RT] = Field(default_factory=list)


class APCreateRequest(BaseModel):
    index: int = -1
    num_rts: int = settings.DEFAULT_RTS_PER_AP
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS


class Message(BaseModel):
    message: str
