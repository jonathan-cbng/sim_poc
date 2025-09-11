import logging

import httpx
from fastapi import HTTPException, status
from pydantic import Field

from src.api_nms import NmsAuthInfo, NmsHubCreateRequest, NmsNetworkCreateRequest
from src.config import settings
from src.controller.api import APCreateRequest, HubCreateRequest
from src.controller.common import ControllerNode
from src.controller.manager_hub import HubManager


class NetworkManager(ControllerNode):
    csi: str
    csni: str  # CSNI assigned by northbound API

    children: dict[int, HubManager] = Field(default_factory=dict)

    async def add_hub(self, net_index: int, req: HubCreateRequest, index=-1) -> int:
        # Register hub with northbound API
        hub_req = NmsHubCreateRequest(csni=self.csni)
        url = f"{settings.NBAPI_URL}/api/v1/node/hub/{hub_req.auid}"
        headers = NmsAuthInfo().auth_header()
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=hub_req.model_dump(), headers=headers, timeout=10.0)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
        # Proceed with local creation
        index = self.get_index(index)
        hub_mgr = HubManager(index=index, auid=hub_req.auid, parent_index=net_index)
        # Add required number of APs
        for _ in range(req.num_aps):
            ap_req = APCreateRequest(
                num_rts=req.num_rts_per_ap,
                heartbeat_seconds=req.heartbeat_seconds,
                rt_heartbeat_seconds=req.rt_heartbeat_seconds,
            )
            await hub_mgr.add_ap(ap_req)

        self.children[index] = hub_mgr
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

    async def add_network(self, req: NmsNetworkCreateRequest) -> int:
        # Create NetworkManager instance
        net_mgr = await self.create_network(req.csi)

        # Add required number of hubs
        for _ in range(req.hubs):
            hub_req = HubCreateRequest(
                num_aps=req.aps_per_hub,
                num_rts_per_ap=req.rts_per_ap,
                heartbeat_seconds=req.ap_heartbeat_seconds,
            )
            await net_mgr.add_hub(net_index=net_mgr.index, req=hub_req)
        return net_mgr.index

    async def remove_network(self, index) -> None:
        logging.info("Removing Network %d", index)
        self.remove_child(index)

    async def create_network(self, csi) -> NetworkManager:
        """
        Register a network with the real northbound API.
        Args:
            csi (str): Customer CSI string.
        Returns:
            NetworkManager: The created NetworkManager instance.
        """
        url = f"{settings.NBAPI_URL}/api/v1/network/csi/{csi}"
        headers = NmsAuthInfo().auth_header()
        create_req = NmsNetworkCreateRequest()
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=create_req.model_dump(), headers=headers, timeout=10.0)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"{e.request}: {e.response}") from e
        result = resp.json()
        csni = result["csni"]
        index = self.get_index(-1)
        net_mgr = NetworkManager(index=index, csi=csi, csni=csni)
        self.children[index] = net_mgr
        logging.info("Registered network %s to customer %s with northbound API", csni, csi)

        return net_mgr

    def get_network(self, index) -> NetworkManager:
        return self.get_child_or_404(index)

    def get_networks(self) -> dict[int, NetworkManager]:
        return self.children


nms = NMSManager(index=0)  # Singleton instance of the network manager - this is the top-level data structure
