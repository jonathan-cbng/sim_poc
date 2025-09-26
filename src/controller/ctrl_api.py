"""
API request/response models for controller endpoints.
"""

from enum import StrEnum, auto

#######################################################################################################################
# Imports
#######################################################################################################################
from pydantic import BaseModel, Field

from src.config import settings
from src.worker.worker_api import Address

#######################################################################################################################
# Globals
#######################################################################################################################
# ...existing code...
#######################################################################################################################
# Body
#######################################################################################################################


class Result(BaseModel):
    """
    Response model for simple result messages.

    Args:
        message (str): The result message.
    """

    message: str


class RTCreateRequest(BaseModel):
    """
    Request model for creating an AP.

    Args:
        heartbeat_seconds (int): Heartbeat interval in seconds.
    """

    heartbeat_seconds: int = Field(settings.DEFAULT_HEARTBEAT_SECONDS, description="Heartbeat interval in seconds")


class APCreateRequest(BaseModel):
    """
    Request model for creating an AP.

    Args:
        heartbeat_seconds (int): Heartbeat interval in seconds.
        num_rts (int): Number of RTs to create under this AP.
        rt_heartbeat_seconds (int): Heartbeat interval for child RTs.
    """

    heartbeat_seconds: int = Field(settings.DEFAULT_HEARTBEAT_SECONDS, description="Heartbeat interval in seconds")
    num_rts: int = Field(settings.DEFAULT_RTS_PER_AP, description="Number of RTS to create under this AP")
    rt_heartbeat_seconds: int = Field(
        settings.DEFAULT_HEARTBEAT_SECONDS, description="Heartbeat interval in seconds for child RTs"
    )
    azimuth_deg: int = Field(..., description="Azimuth in degrees to set on the AP", ge=0, le=360)


class HubCreateRequest(BaseModel):
    """
    Request model for creating a Hub.

    Args:
        num_aps (int): Number of APs to create under this Hub.
        ap_heartbeat_seconds (int): Heartbeat interval for Hub.
        num_rts_per_ap (int): Number of RTs per AP.
        rt_heartbeat_seconds (int): Heartbeat interval for child RTs.
    """

    num_aps: int = settings.DEFAULT_APS_PER_HUB
    ap_heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS
    num_rts_per_ap: int = settings.DEFAULT_RTS_PER_AP
    rt_heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS


class NetworkCreateRequest(BaseModel):
    """
    Request model for creating a Network.

    Args:
        csi (str): CSI (customer ID).
        email_domain (str): Email domain for users in this network.
        hubs (int): Number of Hubs to create under this network.
        aps_per_hub (int): Number of APs to create under each Hub.
        ap_heartbeat_seconds (int): Heartbeat interval for child APs.
        rts_per_ap (int): Number of RTs to create under each AP.
        rt_heartbeat_seconds (int): Heartbeat interval for child RTs.
    """

    csi: str = Field(default=f"{settings.CSI}", description="CSI (customer ID)", max_length=32)
    email_domain: str = Field(
        default=f"{settings.EMAIL_DOMAIN}", description="Email domain for users in this network", max_length=64
    )
    hubs: int = Field(settings.DEFAULT_HUBS_PER_NETWORK, description="Number of Hubs to create under this network")
    aps_per_hub: int = Field(settings.DEFAULT_APS_PER_HUB, description="Number of APs to create under each Hub")
    ap_heartbeat_seconds: int = Field(
        settings.DEFAULT_HEARTBEAT_SECONDS, description="Heartbeat interval in seconds for child APs"
    )
    rts_per_ap: int = Field(settings.DEFAULT_RTS_PER_AP, description="Number of RTs to create under each AP")
    rt_heartbeat_seconds: int = Field(
        settings.DEFAULT_HEARTBEAT_SECONDS, description="Heartbeat interval in seconds for child RTs"
    )


class RTState(StrEnum):
    """
    Enum for RT registration state.
    """

    UNREGISTERED = auto()
    REGISTERED = auto()
    REGISTRATION_FAILED = auto()


class APState(StrEnum):
    """
    Enum for AP registration state.
    """

    UNREGISTERED = auto()
    REGISTERED = auto()
    REGISTRATION_FAILED = auto()


class HubState(StrEnum):
    """
    Enum for Hub registration state.
    """

    UNREGISTERED = auto()
    REGISTERED = auto()


class NetworkState(StrEnum):
    """
    Enum for Network registration state.
    """

    UNREGISTERED = auto()
    REGISTERED = auto()


class NetworkRead(BaseModel):
    """
    Response model for reading a Network.

    Args:
        index (int): Network index.
        csi (str): CSI (customer ID).
        csni (str): CSNI (network identifier).
        state (str): Current state of the network.
    """

    address: Address = Field(..., description="Network address")
    csi: str = Field(..., description="CSI (customer ID)")
    csni: str = Field(..., description="CSNI (network identifier)")
    state: NetworkState = Field(..., description="Current state of the network")


#######################################################################################################################
# End of file
#######################################################################################################################
