import logging
import uuid

import httpx
from pydantic import Field
from starlette.status import HTTP_200_OK, HTTP_300_MULTIPLE_CHOICES

from src.api_nms import AuthInfo
from src.config import settings
from src.controller.api import APCreateRequest, HubCreateRequest, NetworkCreateRequest
from src.controller.common import Node
from src.controller.manager_hub import HubManager


class NetworkManager(Node):
    csi: str = Field(default_factory=lambda: str(uuid.uuid4()))

    children: dict[int, HubManager] = Field(default_factory=dict)

    async def add_hub(self, net_index: int, req: HubCreateRequest, index=-1) -> int:
        index = self.get_index(index)
        hub_mgr = HubManager(index=index, auid=req.auid, parent_index=net_index)
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


class NMSManager(Node):
    children: dict[int, NetworkManager] = Field(default_factory=dict)

    async def add_network(self, req: NetworkCreateRequest, index=-1) -> int:
        index = self.get_index(index)  # Will throw HTTPError if already exists
        # Create NetworkManager instance
        net_mgr = NetworkManager(index=index, csi=req.csi)
        # Add required number of hubs
        for _ in range(req.hubs):
            hub_req = HubCreateRequest(
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

    async def register_network_northbound(self, req: NetworkCreateRequest, csi: str) -> tuple[str, bool]:
        """
        Register a network with the real northbound API.
        Args:
            req (NetworkCreateRequest): The network creation request body.
            csi (str): Customer CSI string.
        Returns:
            tuple[str, bool]: (response_text, success)
        """
        url = f"{settings.NBAPI_URL}/api/v1/network/csi/{csi}"
        headers = {"Bearer": AuthInfo().jwt()}
        verify = getattr(settings, "VERIFY_SSL_CERT", True)
        timeout = 60.0
        async with httpx.AsyncClient(verify=verify, timeout=timeout) as client:
            try:
                res = await client.post(
                    url,
                    json=req.model_dump(),
                    headers=headers,
                )
                response_text = res.text
                if HTTP_200_OK <= res.status_code < HTTP_300_MULTIPLE_CHOICES:
                    logging.debug(f"Registered network northbound: {response_text}")
                    return response_text, True
                else:
                    logging.info(
                        f"Error registering network northbound. Status: {res.status_code}. Response: {response_text}"
                    )
                    return response_text, False
            except Exception as e:
                logging.info(f"Exception posting to northbound: {e}")
                return str(e), False


nms = NMSManager(index=0)  # Singleton instance of the network manager - this is the top-level data structure
