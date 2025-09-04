import logging
import uuid
from enum import Enum, auto
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from src.config import settings


class Node(BaseModel):
    index: int
    parent_index: int | None = None
    children: dict[int, Any] = Field(default_factory=dict)

    def get_index(self, requested: int) -> int:
        """
        Returns the lowest non-negative integer not in used_indices.
        """
        if requested < 0:
            used_indices = set(self.children.keys())
            idx = 0
            while idx in used_indices:
                idx += 1
            return idx
        elif requested in self.children:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Index {requested} already in use")
        else:
            return requested

    def get_child_or_404(self, index: int) -> Any:
        try:
            return self.children[index]
        except KeyError as err:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"index {index} not found") from err

    def remove_child(self, index) -> None:
        """
        Stop and remove a Hub and all underlying APs and RTs.
        """
        try:
            logging.info("%s:%d: Removing child %d", self.__class__.__name__, self.index, index)
            del self.children[index]
        except KeyError as err:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Child not found") from err


class RT(Node):
    auid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS


class APState(Enum):
    STARTING = auto()
    CONNECTED = auto()
    REGISTERED = auto()


class AP(Node):
    state: APState = APState.STARTING
    auid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS
