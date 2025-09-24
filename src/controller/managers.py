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
from typing import Any

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, Field, PrivateAttr
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from src.config import settings
from src.controller.comms import worker_ctrl
from src.controller.ctrl_api import (
    APCreateRequest,
    APState,
    HubCreateRequest,
    HubState,
    NetworkState,
    RTCreateRequest,
    RTState,
)
from src.nms_api import NmsAuthInfo, NmsHubCreateRequest
from src.worker.worker_api import Address, APRegisterReq, APRegisterRsp, HubConnectInd, RTRegisterReq, StartHeartbeatReq

#######################################################################################################################
# Body
#######################################################################################################################


class ParentNode(BaseModel):
    """
    Mixin class for parent nodes that manage child nodes.
    """

    children: dict[int, Any] = Field(default_factory=dict, description="Child nodes of this node")
    address: Address = Field(description="The address of this node - sort of a fully qualified name")
    auid_prefix: str = Field(default="", description="Prefix for child AP AUIDs")

    @property
    def auid(self):
        return f"{self.auid_prefix}{self.address.tag}"

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


class RTManager(ParentNode):
    """
    Manager for RT nodes.

    Args:
        state (src.controller.ctrl_api.RTState): Registration state.
        heartbeat_seconds (int): Heartbeat interval.
    """

    ap_auid: str = Field(description="The auid of the parent AP")

    state: RTState = RTState.UNREGISTERED
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS
    azimuth_deg: int = Field(default=0, ge=0, le=360)

    _registered_event: asyncio.Event = PrivateAttr()

    def model_post_init(self, __context):
        self._registered_event = asyncio.Event()

    async def register(self):
        """
        Wait until the AP is registered or registration failed.

        Returns:
            asyncio.Event: Event that is set when registration completes.
        """
        register_req = RTRegisterReq(
            address=self.address,
            heartbeat_seconds=self.heartbeat_seconds,
            ap_auid=self.ap_auid,
            auid=self.auid,
        )
        worker_ctrl.send(register_req)

        await self._registered_event.wait()

    def on_rt_register_rsp(self, msg: APRegisterRsp):
        """
        Handle APRegisterRsp message from worker.

        Args:
            msg (APRegisterRsp): The AP registration response message.
        """
        self.state = RTState.REGISTERED if msg.success else RTState.REGISTRATION_FAILED
        if msg.success:
            logging.debug(f"RT {self.address.tag} registered successfully.")
        else:
            logging.error(f"RT {self.address.tag} registration failed.")

        self._registered_event.set()

    def start_heartbeats(self):
        """
        Start heartbeat tasks for all APs and RTs in the hub
        """
        msg = StartHeartbeatReq(address=self.address)
        worker_ctrl.send(msg)


class APManager(ParentNode):
    """
    Manager for AP nodes.

    Args:
        state (src.controller.ctrl_api.APState): Registration state.
        heartbeat_seconds (int): Heartbeat interval.
        hub_auid (str): AUID of parent Hub.
    """

    children: dict[int, RTManager] = Field(default_factory=dict)
    state: APState = APState.UNREGISTERED
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS
    hub_auid: str = Field(description="The auid of the parent AP")

    _registered_event: asyncio.Event = PrivateAttr()

    def model_post_init(self, __context):
        self._registered_event = asyncio.Event()

    async def add_rt(self, req: RTCreateRequest, rt_idx: int = -1) -> RTManager:
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
        rt_idx = self.get_index(rt_idx)

        rt_address = Address(net=self.address.net, hub=self.address.hub, ap=self.address.ap, rt=rt_idx)
        self.children[rt_idx] = rt = RTManager(
            address=rt_address, heartbeat_seconds=req.heartbeat_seconds, ap_auid=self.auid, auid_prefix=self.auid_prefix
        )
        await rt.register()
        logging.info(f"Created RT {rt.address}")
        return rt

    def get_rt(self, index: int) -> RTManager:
        """
        Get an RTManager by index.

        Args:
            index (int): RT index.

        Returns:
            RTManager: The RTManager instance.
        """
        return self.get_child_or_404(index)

    def on_ap_register_rsp(self, msg: APRegisterRsp):
        """
        Handle APRegisterRsp message from worker.

        Args:
            msg (APRegisterRsp): The AP registration response message.
        """
        self.state = APState.REGISTERED if msg.success else APState.REGISTRATION_FAILED
        if msg.success:
            logging.debug(f"AP {self.address.tag} registered successfully.")
        else:
            logging.error(f"AP {self.address.tag} registration failed.")

        self._registered_event.set()

    async def register(self):
        """
        Wait until the AP is registered or registration failed.

        Returns:
            asyncio.Event: Event that is set when registration completes.
        """
        ap_req = APRegisterReq(
            address=self.address,
            heartbeat_seconds=self.heartbeat_seconds,
            hub_auid=self.hub_auid,
            auid=self.auid,
        )
        worker_ctrl.send(ap_req)

        await self._registered_event.wait()

    def start_heartbeats(self, recursive: bool = False):
        """
        Start heartbeat tasks for all APs and RTs in the hub
        """
        msg = StartHeartbeatReq(address=self.address)
        worker_ctrl.send(msg)
        if recursive:
            for rt in self.children.values():
                rt.start_heartbeats()


class HubManager(ParentNode):
    """
    Manager for Hub nodes.
    """

    state: HubState = HubState.UNREGISTERED
    children: dict[int, APManager] = Field(default_factory=dict)
    auid_prefix: str = Field(default="", description="Prefix for child AP AUIDs")

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
            address=ap_address,
            heartbeat_seconds=req.heartbeat_seconds,
            hub_auid=self.auid,
            auid_prefix=self.auid_prefix,
        )
        self.children[ap_idx] = new_ap
        await new_ap.register()

        req_params = RTCreateRequest(heartbeat_seconds=req.rt_heartbeat_seconds)
        # Batch the add_rt calls using asyncio.gather for concurrency
        rt_add_tasks = [new_ap.add_rt(req_params, i) for i in range(req.num_rts)]
        await asyncio.gather(*rt_add_tasks)
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

    def start_heartbeats(self):
        """
        Start heartbeat tasks for all APs and RTs in the hub
        """
        for ap in self.children.values():
            ap.start_heartbeats(recursive=True)

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self.stop_worker()


class NetworkManager(ParentNode):
    """
    Manager for Network nodes.

    Args:
        csi (str): Customer ID.
        csni (str): CSNI assigned by northbound API.
        state (src.controller.ctrl_api.NetworkState): Registration state.
        children (dict[int, HubManager]): Hub managers.
    """

    csi: str
    csni: str
    state: NetworkState = NetworkState.UNREGISTERED
    children: dict[int, HubManager] = Field(default_factory=dict)

    async def add_hub(self, req: HubCreateRequest, index: int = -1) -> HubManager:
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
        hub_mgr = HubManager(address=hub_address, auid_prefix=f"{self.csni}_")
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

        hub_mgr.state = HubState.REGISTERED

        ap_add_requests = [
            hub_mgr.add_ap(
                APCreateRequest(
                    num_rts=req.num_rts_per_ap,
                    heartbeat_seconds=req.heartbeat_seconds,
                    rt_heartbeat_seconds=req.rt_heartbeat_seconds,
                    azimuth_deg=round(i * (360.0 / req.num_aps)),
                ),
            )
            for i in range(req.num_aps)
        ]
        await asyncio.gather(*ap_add_requests)
        return hub_mgr

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

    def start_heartbeats(self):
        """
        Start heartbeat tasks for all Hubs, APs, and RTs in the network.
        """
        for hub in self.children.values():
            hub.start_heartbeats()


#######################################################################################################################
# End of file
#######################################################################################################################
