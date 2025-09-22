"""
rt.py

Defines the RT (Remote Terminal) class for the network simulation worker. Handles RT state and communication with the
controller.

This module is responsible for simulating Remote Terminals (RTs) in the network simulation. The RT class inherits from
Node and communicates with the controller via WorkerComms.

Usage:
    Used internally by the worker process to manage RT lifecycle and state.
"""

import logging

import httpx
import shortuuid

from src.api_nms import NmsAuthInfo, NmsRTCreateRequest, NmsRTRegisterParam, NmsRTRegisterRequest
from src.config import settings
from src.worker.api_types import RTRegisterReq, RTRegisterRsp

#######################################################################################################################
# Imports
#######################################################################################################################
from src.worker.comms import WorkerComms
from src.worker.node import Node

#######################################################################################################################
# Globals
#######################################################################################################################

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
        self.parent_auid = command.ap_auid
        self.heartbeat_secs = command.heartbeat_seconds
        self.auid = command.auid
        self.azimuth_deg = command.azimuth_deg
        self.token = shortuuid.uuid()

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
                    lat_deg=51.5072,  # or use a value from command if available
                    lon_deg=0.1276,  # or use a value from command if available
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
                reg_payload = NmsRTRegisterRequest(
                    params=[
                        NmsRTRegisterParam(name="imei", type="blank", value=self.auid),
                        NmsRTRegisterParam(name="rt.nms.rt_access_token", type="blank", value=self.token),
                    ]
                )
                candidate_headers = {"Authorization": f"Bearer {self.token}"}
                res = await client.post(
                    f"{settings.SBAPI_URL}/api/v1/T-{self.auid}/rt-registration",
                    json=reg_payload.model_dump(),
                    headers=candidate_headers,
                )
                res.raise_for_status()

                logging.info(f"{self.address.tag}: RT registration successful (AUID: {self.auid})")
                response = RTRegisterRsp(success=True, address=self.address)
        except Exception as e:
            logging.error(f"Exception during AP registration: {e}")
            response = RTRegisterRsp(success=False, address=self.address)

        # TODO: start heartbeat task here
        return response


#######################################################################################################################
# End of file
#######################################################################################################################
