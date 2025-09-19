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

from src.api_nms import NmsAuthInfo, NmsHubCreateRequest, NmsNetworkCreateRequest
from src.config import settings
from src.controller.api import APCreateRequest, HubCreateRequest, NetworkCreateRequest
from src.worker.worker_api import Address, HubConnectInd


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


class RTState(StrEnum):
    UNREGISTERED = auto()
    REGISTERED = auto()


class RTManager(ControllerNode):
    state: RTState = RTState.UNREGISTERED
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS


class APState(StrEnum):
    UNREGISTERED = auto()
    REGISTERED = auto()


class APManager(ControllerNode):
    state: APState = APState.UNREGISTERED
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS
    hub_auid: str  # AUID of parent Hub, filled in when the AP is created registers

    def get_rt(self, index) -> RTManager:
        return self.get_child_or_404(index)


class HubManager(ControllerNode):
    class State(StrEnum):
        UNREGISTERED = auto()
        REGISTERED = auto()

    state: State = State.UNREGISTERED
    children: dict[int, APManager] = {}

    _worker: subprocess.Popen | None = PrivateAttr(default=None)
    _connected_event: asyncio.Event = PrivateAttr(default_factory=asyncio.Event)

    async def add_ap(self, req: APCreateRequest, ap_idx=-1) -> APManager:
        """
        Create & start an AP (optionally with initial RTs). If req.ap_id is
        -1, then a new ID will be assigned automatically. Once added to the local list,
        we start the AP simulator process.

        :param req: APCreateRequest object containing parameters for the new AP
        :return: The created AP object
        :raises HTTPException: If the specified index already exists

        """
        ap_idx = self.get_index(ap_idx)  # Will throw HTTPError if already exists
        ap_address = Address(net=self.address.net, hub=self.address.hub, ap=ap_idx)
        new_ap = APManager(
            index=ap_idx,
            parent_index=self.index,
            address=ap_address,
            heartbeat_seconds=req.heartbeat_seconds,
            hub_auid=self.auid,
        )
        self.children[ap_idx] = new_ap
        rts = {}
        for i in range(req.num_rts):
            rt_address = Address(net=self.address.net, hub=self.address.hub, ap=ap_idx, rt=i)
            rts[i] = RTManager(
                index=i, parent_index=new_ap.index, address=rt_address, heartbeat_seconds=req.heartbeat_seconds
            )

        new_ap.children = rts
        logging.info("Created AP %d with %d RTs", ap_idx, req.num_rts)
        return new_ap

    async def remove_ap(self, id):
        """
        Stop and remove an AP and all underlying RTs. Once the AP has indicated it has stopped,
        then the handling process can also be terminated.
        """
        logging.info("Removing AP %d", id)
        self.remove_child(id)

    def get_ap(self, index) -> APManager:
        return self.get_child_or_404(index)

    def on_connect_ind(self, msg: HubConnectInd):
        logging.info(f"Worker connected: {msg.address}")
        self._connected_event.set()

    async def start_worker(self) -> None:
        """Start the hub worker process and wait for it to connect back."""

        self._worker = subprocess.Popen(
            [
                "python",
                "-u",  # Force unbuffered output for logging
                "-m",
                "src.worker.worker",
                str(self.address.net),  # network_idx
                str(self.address.hub),  # hub_idx
                f"tcp://127.0.0.1:{settings.PUB_PORT}",
                f"tcp://127.0.0.1:{settings.PULL_PORT}",
            ]
        )
        logging.info("Hub %s Worker started.", self.address.tag)
        await self._connected_event.wait()  # Will be set by on_connect_ind when the worker connects

    def stop_worker(self):
        if self._worker:
            logging.info("Terminating hub worker process for hub %d", self.address)
            self._worker.terminate()
            try:
                self._worker.wait(timeout=5)
            except Exception as e:
                logging.warning(f"Worker process for hub {self.index} did not exit cleanly: {e}")
            self._worker = None

    def __del__(self):
        with contextlib.suppress(Exception):
            self.stop_worker()


class NetworkState(StrEnum):
    UNREGISTERED = auto()
    REGISTERED = auto()


class NetworkManager(ControllerNode):
    csi: str
    csni: str  # CSNI assigned by northbound API
    state: NetworkState = NetworkState.UNREGISTERED

    children: dict[int, HubManager] = Field(default_factory=dict)

    async def add_hub(self, req: HubCreateRequest, index=-1) -> int:
        index = self.get_index(index)
        hub_address = Address(net=self.address.net, hub=index)
        hub_mgr = HubManager(index=index, parent_index=self.address.net, address=hub_address)
        self.children[index] = hub_mgr  # This needs to be added here so that worker messages are routed correctly
        # Proceed with local manager creation (and worker process start)
        await hub_mgr.start_worker()  # Starts the worker process and waits for it to connect

        # Register hub with northbound API
        hub_req = NmsHubCreateRequest(csni=self.csni, auid=hub_mgr.auid)
        url = f"{settings.NBAPI_URL}/api/v1/node/hub/{hub_req.auid}"
        async with httpx.AsyncClient(headers=NmsAuthInfo().auth_header(), timeout=settings.HTTPX_TIMEOUT) as client:
            try:
                resp = await client.post(url, json=hub_req.model_dump())
                resp.raise_for_status()
            except httpx.HTTPError as e:
                del self.children[index]
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e

        # Add required number of APs
        for _ in range(req.num_aps):
            ap_req = APCreateRequest(
                num_rts=req.num_rts_per_ap,
                heartbeat_seconds=req.heartbeat_seconds,
                rt_heartbeat_seconds=req.rt_heartbeat_seconds,
            )
            await hub_mgr.add_ap(ap_req)

        return index

    async def remove_hub(self, index):
        logging.info("Removing Hub %d from Network %d", index, self.index)
        self.remove_child(index)

    def get_hub(self, index) -> HubManager:
        return self.get_child_or_404(index)

    def get_hubs(self) -> dict[int, HubManager]:
        return self.children


class NMSManager(ControllerNode):
    children: dict[int, NetworkManager] = Field(default_factory=dict)

    async def add_network(self, req: NetworkCreateRequest) -> int:
        # Create NetworkManager instance
        url = f"{settings.NBAPI_URL}/api/v1/network/csi/{req.csi}"

        create_req = NmsNetworkCreateRequest(customer_contact_email=f"tester@{req.email_domain}")
        async with httpx.AsyncClient(headers=NmsAuthInfo().auth_header(), timeout=settings.HTTPX_TIMEOUT) as client:
            try:
                resp = await client.post(url, json=create_req.model_dump())
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"{e.request}: {e.response}") from e

        result = resp.json()
        csni = result["csni"]
        index = self.get_index(-1)
        address = Address(net=index)
        net_mgr = NetworkManager(
            index=index, parent_index=self.index, address=address, csi=req.csi, csni=csni, state=NetworkState.REGISTERED
        )
        self.children[index] = net_mgr
        logging.info("Registered network %s to customer %s with northbound API", csni, req.csi)

        # Add required number of hubs
        for _ in range(req.hubs):
            hub_req = HubCreateRequest(
                num_aps=req.aps_per_hub,
                num_rts_per_ap=req.rts_per_ap,
                heartbeat_seconds=req.ap_heartbeat_seconds,
            )
            await net_mgr.add_hub(req=hub_req)
        return net_mgr.index

    async def remove_network(self, index) -> None:
        logging.info("Removing Network %d", index)
        self.remove_child(index)

    def get_network(self, index) -> NetworkManager:
        return self.get_child_or_404(index)

    def get_networks(self) -> dict[int, NetworkManager]:
        return self.children

    def get_node(self, address: Address):
        """
        Resolve this address to the correct manager node in the NMS hierarchy.

        Args:
            nms: The network management system instance.

        Returns:
            The object at this address.
        """
        instance = self.get_network(address.net)
        if address.hub is not None:
            instance = instance.get_hub(address.hub)
            if address.ap is not None:
                instance = instance.get_ap(address.ap)
                if address.rt is not None:
                    instance = instance.get_rt(address.rt)
        return instance


nms = NMSManager(
    index=0, address=Address()
)  # Singleton instance of the network manager - this is the top-level data structure
