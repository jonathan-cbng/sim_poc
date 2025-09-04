import logging
import uuid

from pydantic import Field

from src.common import Node
from src.manager_hub import HubManager
from src.models_api import APCreateRequest, HubCreateRequest, NetworkCreateRequest


class NetworkManager(Node):
    csni: str = Field(default_factory=lambda: str(uuid.uuid4()))

    children: dict[int, HubManager] = Field(default_factory=dict)

    async def add_hub(self, net_index: int, req: HubCreateRequest, index=-1) -> int:
        index = self.get_index(index)
        hub_mgr = HubManager(index=index, auid=req.auid, net_index=net_index)
        # Add required number of APs
        for _ in range(req.num_aps):
            ap_req = APCreateRequest(
                hub_index=index, num_rts=req.num_rts_per_ap, heartbeat_seconds=req.heartbeat_seconds
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


class NMSManager(Node):
    children: dict[int, NetworkManager] = Field(default_factory=dict)

    async def add_network(self, req: NetworkCreateRequest, index=-1) -> int:
        index = self.get_index(index)  # Will throw HTTPError if already exists
        # Create NetworkManager instance
        net_mgr = NetworkManager(index=index, csni=req.csni)
        # Add required number of hubs
        for i in range(req.hubs):
            hub_req = HubCreateRequest(
                index=i,
                auid=str(uuid.uuid4()),
                num_aps=req.aps_per_hub,
                num_rts_per_ap=req.rts_per_ap,
                heartbeat_seconds=req.ap_heartbeat_seconds,
            )
            await net_mgr.add_hub(net_index=index, req=hub_req)
        self.children[index] = net_mgr
        return index

    async def remove_network(self, index) -> None:
        logging.info("Removing Network %d", index)
        self.remove_child(index)

    def get_network(self, index) -> NetworkManager:
        return self.get_child_or_404(index)

    def get_networks(self) -> dict[int, NetworkManager]:
        return self.children


nms = NMSManager(index=0)  # Singleton instance of the network manager - this is the top-level data structure
