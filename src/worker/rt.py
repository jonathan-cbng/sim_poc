"""
rt.py

Defines the RT (Remote Terminal) class for the network simulation worker. Handles RT state and communication with the
controller.

This module is responsible for simulating Remote Terminals (RTs) in the network simulation. The RT class inherits from
Node and communicates with the controller via WorkerComms.

Usage:
    Used internally by the worker process to manage RT lifecycle and state.
"""

#######################################################################################################################
# Imports
#######################################################################################################################

import asyncio
import logging
import math
from random import random

from src.config import settings
from src.nms_api import NmsAuthInfo, NmsRTCreateRequest, NmsRTRegisterParam, NmsRTRegisterRequest
from src.worker.comms import WorkerComms
from src.worker.node import Node
from src.worker.utils import fix_execution_time, zero_centred_rand
from src.worker.worker_api import RTRegisterReq, RTRegisterRsp

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

    def __init__(self, address, http_client, comms: WorkerComms):
        """
        Initialize an RT instance.

        Args:
            address: The address of the RT node.
            comms (WorkerComms): Communication link to the controller.
        """
        super().__init__(address, http_client, comms)
        self.heartbeat_secs = None
        self.auid = None
        self.heartbeat_task = None
        self.registered = False

    async def heartbeat(self):
        """
        Send periodic heartbeat messages to the SBAPI to indicate the RT is alive.
        """
        await asyncio.sleep(self.heartbeat_secs * random())  # Avoids thundering herd
        while True:
            async with fix_execution_time(self.heartbeat_secs, f"RT {self.address.tag}", logging):
                logging.debug(f"RT {self.address.tag}: {self.heartbeat_secs}s heartbeat")
                try:
                    rt_token = NmsAuthInfo.rt_jwt(self.auid)
                    candidate_headers = {"Authorization": f"Bearer {rt_token}"}
                    res = await self.http_client.post(
                        f"{settings.SBAPI_URL}/api/v1/{self.auid}/heartbeat", json={}, headers=candidate_headers
                    )
                    res.raise_for_status()
                    self.record_hb(True)
                except Exception:
                    self.record_hb(False)
                    logging.warning(f"RT {self.address.tag}: Heartbeat failed", exc_info=True)

    async def on_rt_register_req(self, command: RTRegisterReq) -> RTRegisterRsp | None:
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
        self.heartbeat_secs = command.heartbeat_seconds
        self.auid = command.auid
        self.azimuth_deg = command.azimuth_deg

        temp_auid = f"T-{self.auid}"
        try:
            # Step 1: Create RT in NBAPI
            rt_payload = NmsRTCreateRequest(
                auid=temp_auid,
                id=f"ID{self.auid}",
                name=f"NAME{self.auid}",
                parent_auid=self.parent.auid,
                node_priority="Gold",
                node_status="Active",
                address="NONE",
                lat_deg=self.parent.lat_deg + zero_centred_rand(MAX_AP_RT_DEG),
                lon_deg=self.parent.lon_deg + zero_centred_rand(MAX_AP_RT_DEG),
                height_mast_m=20,
                height_asl_m=21,
                notes="NONE",
                # network_details={"rt_wwan_1_ipv6_address": None},
                network_details={"rt_wwan_1_ipv6_address": self.address.ipv6_address},
            )
            res = await self.http_client.post(
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
            res = await self.http_client.post(
                f"{settings.SBAPI_URL}/api/v1/T-{self.auid}/rt-registration",
                json=reg_payload.model_dump(),
                headers=candidate_headers,
            )
            res.raise_for_status()

            logging.info(f"{self.address.tag}: RT registration successful (AUID: {self.auid})")
            self.registered = True
            response = RTRegisterRsp(success=True, address=self.address)

        except Exception:
            logging.warning(f"RT {self.address.tag}: Registration failed", exc_info=True)
            response = RTRegisterRsp(success=False, address=self.address)

        return response


#######################################################################################################################
# End of file
#######################################################################################################################
