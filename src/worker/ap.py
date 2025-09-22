import logging
from datetime import UTC, datetime

import httpx
import shortuuid

from src.api_nms import (
    NmsAPCreateRequest,
    NmsAuthInfo,
    RegisterAPCandidateHeaders,
    RegisterAPCandidateRequest,
    RegisterAPSecretHeaders,
)
from src.config import settings
from src.worker.comms import ControllerLink
from src.worker.node import Node
from src.worker.worker_api_types import APRegisterReq, APRegisterRsp


class AP(Node):
    """
    Class representing an Access Point (AP) in the network simulation.
    """

    def __init__(self, address, comms: ControllerLink):
        super().__init__(address, comms)
        self.parent_auid = None
        self.heartbeat_secs = None
        self.auid = None
        self.azimuth_deg = None
        self.ap_secret = None

    async def process_register_req(self, command: APRegisterReq):
        """
        Handle an AP registration request.

        Registration process overview:
        1. The AP is created in the NBAPI (Network Backend API) with its configuration and parent hub.
        2. The AP's secret is registered with the SBAPI (Service Backend API) using the AP's AUID and secret.
        3. The AP is registered as a candidate in the SBAPI, providing the customer CSI, installer key, and chosen AUID.
        4. If any step fails, the registration process is aborted for this AP.
        5. On success, the AP is considered registered and ready for further provisioning.

        This method performs the registration and sends an APRegisterInd message back to the controller on success.
        """
        self.parent_auid = command.hub_auid
        self.heartbeat_secs = command.heartbeat_seconds
        self.auid = command.auid
        self.azimuth_deg = command.azimuth_deg
        self.ap_secret = shortuuid.uuid()

        temp_auid = f"T-{self.auid}"
        # Compose AP creation payload using Pydantic model
        ap_payload = NmsAPCreateRequest(
            auid=temp_auid,
            id=f"ID_{self.auid}",
            name=f"NAME_{self.auid}",
            parent_auid=self.parent_auid,
            azimuth_deg=self.azimuth_deg,
        )

        try:
            async with httpx.AsyncClient(
                timeout=settings.HTTPX_TIMEOUT, verify=settings.VERIFY_SSL_CERT, follow_redirects=True
            ) as client:
                # Step 1: Create AP in NBAPI
                res = await client.post(
                    f"{settings.NBAPI_URL}/api/v1/node/ap/{temp_auid}",
                    json=ap_payload.model_dump(),
                    headers=NmsAuthInfo().auth_header(),
                )
                res.raise_for_status()

                # Step 2: Register AP secret in SBAPI using Pydantic headers
                secret_headers = RegisterAPSecretHeaders(gnodebid=self.auid, secret=self.ap_secret)
                res = await client.post(
                    f"{settings.SBAPI_URL}/ap/register_secret/", json={}, headers=secret_headers.model_dump()
                )
                res.raise_for_status()

                # Step 3: Register AP as candidate in SBAPI using Pydantic models
                candidate_payload = RegisterAPCandidateRequest(
                    csi=settings.CSI,
                    installer_key=settings.INSTALLER_KEY,
                    chosen_auid=temp_auid,
                )
                candidate_headers = RegisterAPCandidateHeaders(gnodebid=self.auid, secret=self.ap_secret)
                res = await client.post(
                    f"{settings.SBAPI_URL}/ap/register_candidate",
                    json=candidate_payload.model_dump(),
                    headers=candidate_headers.model_dump(),
                )
                res.raise_for_status()

                # Registration successful
                logging.info("%s: AP registration successful (AUID: %s)", self.address.tag, self.auid)
        except Exception as e:
            logging.error(f"Exception during AP registration: {e}")
            return

        response = APRegisterRsp(address=self.address, registered_at=datetime.now(UTC).isoformat())

        # TODO: start heartbeat task here
        return response
