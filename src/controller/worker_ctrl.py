"""
Worker controller for managing communication with worker processes via ZeroMQ.
"""

import asyncio

#######################################################################################################################
# Imports
#######################################################################################################################
import logging

import httpx
from fastapi import HTTPException
from starlette import status

from src.config import settings
from src.controller.comms import ControllerComms
from src.controller.ctrl_api import HubCreateRequest, NetworkCreateRequest
from src.controller.managers import APManager, HubManager, NetworkManager, NetworkState, ParentNode, RTManager
from src.nms_api import NmsAuthInfo, NmsNetworkCreateRequest
from src.worker.worker_api import Address, MessageTypes

#######################################################################################################################
# Globals
#######################################################################################################################
# ...existing code...
#######################################################################################################################
# Body
#######################################################################################################################


class SimulatorManager(ParentNode):
    """
    Top-level manager for the NMS network simulator.

    This class is intended to be a singleton instance that manages all networks. As such it also manages the ZeroMQ
    context and sockets for communication with worker processes (which are children of HubManager instances).
    """

    def model_post_init(self, context):
        self.children: dict[int, NetworkManager] = {}

    async def add_network(self, req: NetworkCreateRequest) -> NetworkManager:
        """
        Add a Network to the NMS and register it with the northbound API.

        Args:
            req (NetworkCreateRequest): Network creation request.

        Returns:
            int: The index of the created Network.
        """
        url = f"{settings.NBAPI_URL}/api/v1/network/csi/{req.csi}"
        create_req = NmsNetworkCreateRequest(customer_contact_email=f"tester@{req.email_domain}")
        async with httpx.AsyncClient(headers=NmsAuthInfo().auth_header(), timeout=settings.HTTPX_TIMEOUT) as client:
            try:
                resp = await client.post(url, json=create_req.model_dump())
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"{e}") from e
        result = resp.json()
        csni = result["csni"]
        index = self.get_index(-1)
        address = Address(net=index)
        net_mgr = NetworkManager(address=address, csi=req.csi, csni=csni, state=NetworkState.REGISTERED)
        self.children[index] = net_mgr
        logging.info(f"Registered network {csni} to customer {req.csi} with northbound API")
        hub_reqs = [
            net_mgr.add_hub(
                req=HubCreateRequest(
                    num_aps=req.aps_per_hub,
                    num_rts_per_ap=req.rts_per_ap,
                    heartbeat_seconds=req.ap_heartbeat_seconds,
                )
            )
            for _ in range(req.hubs)
        ]
        await asyncio.gather(*hub_reqs)
        return net_mgr

    async def remove_network(self, index: int) -> None:
        """
        Remove a Network from the NMS.

        Args:
            index (int): Network index.
        """
        logging.info(f"Removing Network {index}")
        self.remove_child(index)

    def get_network(self, index: int) -> NetworkManager:
        """
        Get a NetworkManager by index.

        Args:
            index (int): Network index.

        Returns:
            NetworkManager: The NetworkManager instance.
        """
        return self.get_child_or_404(index)

    def get_networks(self) -> dict[int, NetworkManager]:
        """
        Get all NetworkManagers in the NMS.

        Returns:
            dict[int, NetworkManager]: Dictionary of NetworkManagers keyed by Network ID.
        """
        return self.children

    def get_node(self, address: Address) -> NetworkManager | HubManager | APManager | RTManager:
        """
        Resolve this address to the correct manager node in the NMS hierarchy.

        Args:
            address (Address): The address to resolve.

        Returns:
            Any: The object at this address.
        """
        instance: NetworkManager = self.get_network(address.net)
        if address.hub is not None:
            instance: HubManager = instance.get_hub(address.hub)
            if address.ap is not None:
                instance: APManager = instance.get_ap(address.ap)
                if address.rt is not None:
                    instance: RTManager = instance.get_rt(address.rt)
        return instance

    async def listener(self, worker_ctrl: ControllerComms) -> None:
        """
        Listens for incoming messages from workers on the PULL socket and processes them.

        Args:
            simulator: The SimulatorManager instance to route messages to the correct node.
        """
        while True:
            msg = await worker_ctrl.get_message()
            if msg is not None:
                address = msg.address
                node = self.get_node(address)

                match msg.msg_type:
                    case MessageTypes.HUB_CONNECT_IND:
                        node.on_connect_ind(msg)
                    case MessageTypes.AP_REGISTER_RSP:
                        node.on_ap_register_rsp(msg)
                    case MessageTypes.RT_REGISTER_RSP:
                        node.on_rt_register_rsp(msg)
                    case _:
                        logging.warning(f"Unknown event type: {msg.msg_type}")


simulator = SimulatorManager(
    address=Address()
)  # Singleton instance of the simulator manager - this is the top-level data structure

#######################################################################################################################
# End of file
#######################################################################################################################
