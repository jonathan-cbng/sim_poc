"""
rt.py

Defines the RT (Remote Terminal) class for the network simulation worker. Handles RT state and communication with the
controller.

This module is responsible for simulating Remote Terminals (RTs) in the network simulation. The RT class inherits from
Node and communicates with the controller via WorkerComms.

Usage:
    Used internally by the worker process to manage RT lifecycle and state.
"""

import asyncio
import logging
import math

import httpx

from src.config import settings
from src.nms_api import NmsAuthInfo, NmsRTCreateRequest, NmsRTRegisterParam, NmsRTRegisterRequest
from src.worker.ap import AP

#######################################################################################################################
# Imports
#######################################################################################################################
from src.worker.comms import WorkerComms
from src.worker.node import Node, nodes
from src.worker.utils import zero_centred_rand
from src.worker.worker_api import Address, RTRegisterReq, RTRegisterRsp

#######################################################################################################################
# Globals
#######################################################################################################################

MAX_AP_RT_DIST = 20  # km
EARTH_RADIUS = 6371
MAX_AP_RT_DEG = MAX_AP_RT_DIST / (2 * math.pi * EARTH_RADIUS) * 360 / math.sqrt(2)

#######################################################################################################################
# Body
#######################################################################################################################


class RT(Node):
    """
    Class representing a Remote Terminal (RT) in the network simulation.

    Handles RT state and communication with the controller.

    Args:
        address: The address of the RT node.
        comms (WorkerComms): Communication link to the controller.
    """

    def __init__(self, address, comms: WorkerComms):
        """
        Initialize an RT instance.

        Args:
            address: The address of the RT node.
            comms (WorkerComms): Communication link to the controller.
        """
        super().__init__(address, comms)
        self.parent_auid = None
        self.heartbeat_secs = None
        self.auid = None

    async def heartbeat(self):
        while True:
            logging.debug(f"RT {self.address.tag}: {self.heartbeat_secs}s heartbeat")
            async with httpx.AsyncClient(
                timeout=settings.HTTPX_TIMEOUT, verify=settings.VERIFY_SSL_CERT, follow_redirects=True
            ) as client:
                rt_token = NmsAuthInfo.rt_jwt(self.auid)
                candidate_headers = {"Authorization": f"Bearer {rt_token}"}
                await client.post(
                    f"{settings.SBAPI_URL}/api/v1/{self.auid}/heartbeat", json={}, headers=candidate_headers
                )
            await asyncio.sleep(self.heartbeat_secs)

    async def register_req(self, command: RTRegisterReq) -> RTRegisterRsp | None:
        """
        Handle an AP registration request.

        Registration process overview:
            1. The RT is created in the NBAPI (Network Backend API) with its configuration and parent A{.
            2. The RT is registered to the SBAPI
            3. If any step fails, the registration process is aborted for this AP.
            4. On success, the AP is considered registered and ready for further provisioning.

        This method performs the registration and sends an APRegisterInd message back to the controller on success.

        Args:
            command (RTRegisterReq): The registration request to process
        Returns:
            RTRegisterRsp if successful, None otherwise.
        """
        parent_ap: AP = nodes[Address(net=self.address.net, hub=self.address.hub, ap=self.address.ap)]
        self.parent_auid = command.ap_auid
        self.heartbeat_secs = command.heartbeat_seconds
        self.auid = command.auid
        self.azimuth_deg = command.azimuth_deg

        temp_auid = f"T-{self.auid}"
        try:
            async with httpx.AsyncClient(
                timeout=settings.HTTPX_TIMEOUT, verify=settings.VERIFY_SSL_CERT, follow_redirects=True
            ) as client:
                # Step 1: Create RT in NBAPI
                # Compose RT creation payload using Pydantic model
                rt_payload = NmsRTCreateRequest(
                    auid=temp_auid,
                    id=f"ID{self.auid}",
                    name=f"NAME{self.auid}",
                    parent_auid=self.parent_auid,
                    node_priority="Gold",
                    node_status="Active",
                    address="NONE",
                    lat_deg=parent_ap.lat_deg + zero_centred_rand(MAX_AP_RT_DEG),
                    lon_deg=parent_ap.lon_deg + zero_centred_rand(MAX_AP_RT_DEG),
                    height_mast_m=20,
                    height_asl_m=21,
                    notes="NONE",
                    network_details={"rt_wwan_1_ipv6_address": None},
                )

                res = await client.post(
                    f"{settings.NBAPI_URL}/api/v1/node/rt/T-{self.auid}",
                    json=rt_payload.model_dump(),
                    headers=NmsAuthInfo().auth_header(),
                )
                res.raise_for_status()

                # Step 2: Register RT in SBAPI using Pydantic models
                rt_token = NmsAuthInfo.rt_jwt(self.auid)
                reg_payload = NmsRTRegisterRequest(
                    params=[
                        NmsRTRegisterParam(name="imei", type="blank", value=self.auid),
                        NmsRTRegisterParam(name="rt.nms.rt_access_token", type="blank", value=rt_token),
                    ]
                )
                candidate_headers = {"Authorization": f"Bearer {rt_token}"}
                res = await client.post(
                    f"{settings.SBAPI_URL}/api/v1/T-{self.auid}/rt-registration",
                    json=reg_payload.model_dump(),
                    headers=candidate_headers,
                )
                res.raise_for_status()

                logging.info(f"{self.address.tag}: RT registration successful (AUID: {self.auid})")
                response = RTRegisterRsp(success=True, address=self.address)

                self.heartbeat_task = asyncio.create_task(self.heartbeat())

        except Exception as e:
            logging.error(f"Exception during AP registration: {e}")
            response = RTRegisterRsp(success=False, address=self.address)

        return response


#######################################################################################################################
# End of file
#######################################################################################################################
