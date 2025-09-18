from pydantic import BaseModel, Field

from src.config import settings


class Result(BaseModel):
    message: str


class APCreateRequest(BaseModel):
    heartbeat_seconds: int = Field(settings.DEFAULT_HEARTBEAT_SECONDS, description="Heartbeat interval in seconds")

    num_rts: int = Field(settings.DEFAULT_RTS_PER_AP, description="Number of RTS to create under this AP")
    rt_heartbeat_seconds: int = Field(
        settings.DEFAULT_HEARTBEAT_SECONDS, description="Heartbeat interval in seconds for child RTs"
    )


class HubCreateRequest(BaseModel):
    num_aps: int = settings.DEFAULT_APS_PER_HUB
    num_rts_per_ap: int = settings.DEFAULT_RTS_PER_AP
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS
    rt_heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS


class NetworkCreateRequest(BaseModel):
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
