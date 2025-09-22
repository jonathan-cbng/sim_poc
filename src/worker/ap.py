"""
ap.py

Defines the AP (Access Point) class for the network simulation worker. Handles AP registration with backend APIs and
manages AP state.

This module is responsible for simulating the registration and management of Access Points (APs) in the network
simulation. It interacts with both the Network Backend API (NBAPI) and Service Backend API (SBAPI) to register
APs, secrets, and candidates. The AP class inherits from Node and communicates with the controller via ControllerLink.

Usage:
    Used internally by the worker process to manage AP lifecycle and registration.
"""

#######################################################################################################################
# Imports
#######################################################################################################################

import logging

import httpx
import shortuuid

from src.api_nms import (
    NmsAPCreateRequest,
    NmsAuthInfo,
    NmsRegisterAPCandidateHeaders,
    NmsRegisterAPCandidateRequest,
    NmsRegisterAPSecretHeaders,
)
from src.config import settings
from src.worker.api_types import APRegisterReq, APRegisterRsp
from src.worker.comms import WorkerComms
from src.worker.node import Node

#######################################################################################################################
# Globals
#######################################################################################################################

#######################################################################################################################
# Body
#######################################################################################################################


class AP(Node):
    """
    Class representing an Access Point (AP) in the network simulation.

    Handles registration of the AP with backend APIs and manages AP state.

    Args:
        address: The address of the AP node.
        comms (WorkerComms): Communication link to the controller.
    """

    def __init__(self, address, comms: WorkerComms):
        """
        Initialize an AP instance.

        Args:
            address: The address of the AP node.
            comms (WorkerComms): Communication link to the controller.
        """
        super().__init__(address, comms)
        self.parent_auid = None
        self.heartbeat_secs = None
        self.auid = None
        self.azimuth_deg = None
        self.ap_secret = None

    async def register_req(self, command: APRegisterReq) -> APRegisterRsp | None:
        """
        Handle an AP registration request.

        Registration process overview:
            1. The AP is created in the NBAPI (Network Backend API) with its configuration and parent hub.
            2. The AP's secret is registered with the SBAPI (Service Backend API) using the AP's AUID and secret.
            3. The AP is registered as a candidate in the SBAPI, providing the customer CSI, installer key, and chosen
               AUID.
            4. If any step fails, the registration process is aborted for this AP.
            5. On success, the AP is considered registered and ready for further provisioning.

        This method performs the registration and sends an APRegisterInd message back to the controller on success.

        Args:
            command (APRegisterReq): The AP register request message.

        Returns:
            APRegisterRsp | None: The response message from the AP, or None if registration failed.
        """
        self.parent_auid = command.hub_auid
        self.heartbeat_secs = command.heartbeat_seconds
        self.auid = command.auid
        self.azimuth_deg = command.azimuth_deg
        self.ap_secret = shortuuid.uuid()

        temp_auid = f"T-{self.auid}"
        try:
            async with httpx.AsyncClient(
                timeout=settings.HTTPX_TIMEOUT, verify=settings.VERIFY_SSL_CERT, follow_redirects=True
            ) as client:
                # Step 1: Create AP in NBAPI
                # Compose AP creation payload using Pydantic model
                ap_payload = NmsAPCreateRequest(
                    auid=temp_auid,
                    id=f"ID_{self.auid}",
                    name=f"NAME_{self.auid}",
                    parent_auid=self.parent_auid,
                    azimuth_deg=self.azimuth_deg,
                )

                res = await client.post(
                    f"{settings.NBAPI_URL}/api/v1/node/ap/{temp_auid}",
                    json=ap_payload.model_dump(),
                    headers=NmsAuthInfo().auth_header(),
                )
                res.raise_for_status()

                # Step 2: Register AP secret in SBAPI using Pydantic headers
                secret_headers = NmsRegisterAPSecretHeaders(gnodebid=self.auid, secret=self.ap_secret)
                res = await client.post(
                    f"{settings.SBAPI_URL}/ap/register_secret/", json={}, headers=secret_headers.model_dump()
                )
                res.raise_for_status()

                # Step 3: Register AP as candidate in SBAPI using Pydantic models
                candidate_payload = NmsRegisterAPCandidateRequest(
                    csi=settings.CSI,
                    installer_key=settings.INSTALLER_KEY,
                    chosen_auid=temp_auid,
                )
                candidate_headers = NmsRegisterAPCandidateHeaders(gnodebid=self.auid, secret=self.ap_secret)
                res = await client.post(
                    f"{settings.SBAPI_URL}/ap/register_candidate",
                    json=candidate_payload.model_dump(),
                    headers=candidate_headers.model_dump(),
                )
                res.raise_for_status()

                logging.info(f"{self.address.tag}: AP registration successful (AUID: {self.auid})")
                response = APRegisterRsp(success=True, address=self.address)
        except Exception as e:
            logging.error(f"Exception during AP registration: {e}")
            response = APRegisterRsp(success=False, address=self.address)

        # TODO: start heartbeat task here
        return response


#######################################################################################################################
# End of file
#######################################################################################################################
