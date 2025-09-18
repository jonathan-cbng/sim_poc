import logging
from typing import Any

import shortuuid
from fastapi import HTTPException
from pydantic import BaseModel, Field
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from src.worker.worker_api import Address


class ControllerNode(BaseModel):
    index: int
    parent_index: int | None = None
    children: dict[int, Any] = Field(default_factory=dict)
    address: Address = Field(description="The address of this node - sort of a fully qualified name")
    auid: str = Field(default_factory=shortuuid.uuid, description="The auid of this node")

    def get_index(self, requested: int = -1) -> int:
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
