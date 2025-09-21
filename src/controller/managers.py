"""
Controller node and manager classes for the NMS network simulator.
"""

#######################################################################################################################
# Imports
#######################################################################################################################
import asyncio
import contextlib
import logging
import subprocess
from enum import StrEnum, auto
from typing import Any

import httpx
import shortuuid
from fastapi import HTTPException, status
from pydantic import BaseModel, Field, PrivateAttr
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from src.api_nms import NmsAuthInfo, NmsHubCreateRequest
from src.config import settings
from src.controller.api import APCreateRequest, HubCreateRequest
from src.worker.worker_api import Address, APRegisterReq, HubConnectInd, worker_ctrl

#######################################################################################################################
# Body
#######################################################################################################################


class ParentNodeMixin:
    """
    Mixin class for parent nodes that manage child nodes.
    """

    index: int
    children: dict[int, Any]

    def get_index(self, requested: int = -1) -> int:
        """
        Returns the lowest non-negative integer not in used_indices, or the requested index if available.

        Args:
            requested (int): Requested index, or -1 for auto-assignment.

        Returns:
            int: Assigned index.

        Raises:
            HTTPException: If requested index is already in use.
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
        """
        Get a child node by index or raise HTTP 404 if not found.

        Args:
            index (int): Child index.

        Returns:
            Any: The child node.

        Raises:
            HTTPException: If child not found.
        """
        try:
            return self.children[index]
        except KeyError as err:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"index {index} not found") from err

    def remove_child(self, index: int) -> None:
        """
        Stop and remove a child node by index.

        Args:
            index (int): Child index.

        Raises:
            HTTPException: If child not found.
        """
        try:
            logging.info(f"{self.__class__.__name__}:{self.index}: Removing child {index}")
            del self.children[index]
        except KeyError as err:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Child not found") from err


class ManagerNode(BaseModel):
    """
    Base class for manager nodes in the NMS network simulator.

    Args:
        index (int): Node index.
        children (dict[int, Any]): Child nodes.
        address (Address): Fully qualified address of the node.
        auid (str): Unique node identifier.
    """

    index: int
    address: Address = Field(description="The address of this node - sort of a fully qualified name")
    auid: str = Field(default_factory=shortuuid.uuid, description="The auid of this node")


class RTState(StrEnum):
    """
    Enum for RT registration state.
    """

    UNREGISTERED = auto()
    REGISTERED = auto()


class RTManager(ManagerNode):
    """
    Manager for RT nodes.

    Args:
        state (RTState): Registration state.
        heartbeat_seconds (int): Heartbeat interval.
    """

    state: RTState = RTState.UNREGISTERED
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS


class APState(StrEnum):
    """
    Enum for AP registration state.
    """

    UNREGISTERED = auto()
    REGISTERED = auto()


class APManager(ParentNodeMixin, ManagerNode):
    """
    Manager for AP nodes.

    Args:
        state (APState): Registration state.
        heartbeat_seconds (int): Heartbeat interval.
        hub_auid (str): AUID of parent Hub.
    """

    children: dict[int, RTManager] = Field(default_factory=dict)
    state: APState = APState.UNREGISTERED
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS
    hub_auid: str

    def get_rt(self, index: int) -> RTManager:
        """
        Get an RTManager by index.

        Args:
            index (int): RT index.

        Returns:
            RTManager: The RTManager instance.
        """
        return self.get_child_or_404(index)


class HubState(StrEnum):
    """
    Enum for Hub registration state.
    """

    UNREGISTERED = auto()
    REGISTERED = auto()


class HubManager(ParentNodeMixin, ManagerNode):
    """
    Manager for Hub nodes.
    """

    state: HubState = HubState.UNREGISTERED
    children: dict[int, APManager] = Field(default_factory=dict)

    _worker: subprocess.Popen | None = PrivateAttr(default=None)
    _connected_event: asyncio.Event = PrivateAttr(default_factory=asyncio.Event)

    async def add_ap(self, req: APCreateRequest, ap_idx: int = -1) -> APManager:
        """
        Create & start an AP (optionally with initial RTs).

        Args:
            req (APCreateRequest): AP creation request.
            ap_idx (int): AP index, or -1 for auto-assignment.

        Returns:
            APManager: The created AP object.

        Raises:
            HTTPException: If the specified index already exists.
        """
        ap_idx = self.get_index(ap_idx)
        ap_address = Address(net=self.address.net, hub=self.address.hub, ap=ap_idx)
        new_ap = APManager(
            index=ap_idx,
            address=ap_address,
            heartbeat_seconds=req.heartbeat_seconds,
            hub_auid=self.auid,
        )
        self.children[ap_idx] = new_ap
        ap_req = APRegisterReq(
            address=ap_address,
            heartbeat_seconds=req.rt_heartbeat_seconds,
            hub_auid=self.auid,
            azimuth_deg=req.azimuth_deg,
            auid=new_ap.auid,
        )
        worker_ctrl.send(ap_req)

        rts = {}
        for i in range(req.num_rts):
            rt_address = Address(net=self.address.net, hub=self.address.hub, ap=ap_idx, rt=i)
            rts[i] = RTManager(index=i, address=rt_address, heartbeat_seconds=req.heartbeat_seconds)
        new_ap.children = rts
        logging.info(f"Created AP {ap_idx} with {req.num_rts} RTs")
        return new_ap

    async def remove_ap(self, id: int) -> None:
        """
        Stop and remove an AP and all underlying RTs.

        Args:
            id (int): AP index.
        """
        logging.info(f"Removing AP {id}")
        self.remove_child(id)

    def get_ap(self, index: int) -> APManager:
        """
        Get an APManager by index.

        Args:
            index (int): AP index.

        Returns:
            APManager: The APManager instance.
        """
        return self.get_child_or_404(index)

    def on_connect_ind(self, msg: HubConnectInd) -> None:
        """
        Handle HubConnectInd message from worker.

        Args:
            msg (HubConnectInd): The hub connect indication message.
        """
        logging.info(f"Worker connected: {msg.address}")
        self._connected_event.set()

    async def start_worker(self) -> None:
        """
        Start the hub worker process and wait for it to connect back.
        """
        self._worker = subprocess.Popen(
            [
                "python",
                "-u",
                "-m",
                "src.worker.worker",
                str(self.address.net),
                str(self.address.hub),
                f"tcp://127.0.0.1:{settings.PUB_PORT}",
                f"tcp://127.0.0.1:{settings.PULL_PORT}",
            ]
        )
        logging.info(f"Hub {self.address.tag} Worker started.")
        await self._connected_event.wait()

    def stop_worker(self) -> None:
        """
        Terminate the hub worker process if running.
        """
        if self._worker:
            logging.info(f"Terminating hub worker process for hub {self.address}")
            self._worker.terminate()
            try:
                self._worker.wait(timeout=5)
            except Exception as e:
                logging.warning(f"Worker process for hub {self.index} did not exit cleanly: {e}")
            self._worker = None

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self.stop_worker()


class NetworkState(StrEnum):
    """
    Enum for Network registration state.
    """

    UNREGISTERED = auto()
    REGISTERED = auto()


class NetworkManager(ParentNodeMixin, ManagerNode):
    """
    Manager for Network nodes.

    Args:
        csi (str): Customer ID.
        csni (str): CSNI assigned by northbound API.
        state (NetworkState): Registration state.
        children (dict[int, HubManager]): Hub managers.
    """

    csi: str
    csni: str
    state: NetworkState = NetworkState.UNREGISTERED
    children: dict[int, HubManager] = Field(default_factory=dict)

    async def add_hub(self, req: HubCreateRequest, index: int = -1) -> int:
        """
        Add a Hub to the network and start its worker process.

        Args:
            req (HubCreateRequest): Hub creation request.
            index (int): Hub index, or -1 for auto-assignment.

        Returns:
            int: The index of the created Hub.
        """
        index = self.get_index(index)
        hub_address = Address(net=self.address.net, hub=index)
        hub_mgr = HubManager(index=index, address=hub_address)
        self.children[index] = hub_mgr
        await hub_mgr.start_worker()
        hub_req = NmsHubCreateRequest(csni=self.csni, auid=hub_mgr.auid)
        url = f"{settings.NBAPI_URL}/api/v1/node/hub/{hub_req.auid}"
        async with httpx.AsyncClient(headers=NmsAuthInfo().auth_header(), timeout=settings.HTTPX_TIMEOUT) as client:
            try:
                resp = await client.post(url, json=hub_req.model_dump())
                resp.raise_for_status()
            except httpx.HTTPError as e:
                del self.children[index]
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e

        hub_mgr.state = NetworkState.REGISTERED
        for i in range(req.num_aps):
            ap_req = APCreateRequest(
                num_rts=req.num_rts_per_ap,
                heartbeat_seconds=req.heartbeat_seconds,
                rt_heartbeat_seconds=req.rt_heartbeat_seconds,
                azimuth_deg=round(i * (360.0 / req.num_aps)),
            )
            await hub_mgr.add_ap(ap_req)
        return index

    async def remove_hub(self, index: int) -> None:
        """
        Remove a Hub from the network.

        Args:
            index (int): Hub index.
        """
        logging.info(f"Removing Hub {index} from Network {self.index}")
        self.remove_child(index)

    def get_hub(self, index: int) -> HubManager:
        """
        Get a HubManager by index.

        Args:
            index (int): Hub index.

        Returns:
            HubManager: The HubManager instance.
        """
        return self.get_child_or_404(index)

    def get_hubs(self) -> dict[int, "HubManager"]:
        """
        Get all HubManagers in the network.

        Returns:
            dict[int, HubManager]: Dictionary of HubManagers keyed by Hub ID.
        """
        return self.children


#######################################################################################################################
# End of file
#######################################################################################################################
