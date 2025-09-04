import contextlib
import logging
import subprocess
import uuid
from enum import StrEnum, auto
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, PrivateAttr
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


class APState(StrEnum):
    STARTING = auto()
    CONNECTED = auto()
    REGISTERED = auto()


class AP(Node):
    state: APState = APState.STARTING
    auid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS

    _worker: subprocess.Popen | None = PrivateAttr(default=None)
    _tag: str = PrivateAttr(default=None)

    def start_worker(self, network_idx: int, hub_idx: int, ap_idx: int) -> None:
        # Spawn AP worker process
        self._tag = f"NET{network_idx:04d}HUB{hub_idx:04d}AP{ap_idx:04d}"

        self._worker = subprocess.Popen(
            [
                "python",
                "-m",
                "src.ap_worker",
                str(network_idx),  # network_idx
                str(hub_idx),  # hub_idx
                str(ap_idx),  # ap_idx
                f"tcp://127.0.0.1:{settings.PUB_PORT}",
                f"tcp://127.0.0.1:{settings.PULL_PORT}",
            ]
        )

    def stop_worker(self):
        if self._worker:
            logging.info("Terminating AP worker process for AP %d", self.index)
            self._worker.terminate()
            try:
                self._worker.wait(timeout=5)
            except Exception as e:
                logging.warning(f"AP worker process for AP {self.index} did not exit cleanly: {e}")
            self._worker = None

    def __del__(self):
        with contextlib.suppress(Exception):
            self.stop_worker()
