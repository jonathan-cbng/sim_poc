import time
from datetime import UTC, datetime

import jwt
import shortuuid
from pydantic import BaseModel, Field, model_validator

from src.config import settings
from src.worker.utils import zero_centred_rand


class NmsAuthInfo(BaseModel):
    """
    Authentication and authorization information for a user.
    """

    fullname: str = "Admin McAdminface"
    username: str = "admin"
    services: str = "true"
    expire_day: str = ""
    expire_password: str = ""
    roles: list[str] = Field(default_factory=lambda: ["Read", "Write", "Admin"])
    access_permissions: list[str] = Field(
        default_factory=lambda: [
            "file.overview.read",
            "file.upload.write",
            "file.manage.write",
            "scheduled-jobs.overview.read",
            "scheduled-jobs.manage.write",
            "general.global.write",
            "general.global.read",
        ]
    )
    geolocation_restriction: list[str] = Field(default_factory=list)

    def auth_header(self):
        """
        Generate the authorization header for HTTP requests.
        """
        return {"Authorization": f"Bearer {self.jwt()}"}

    def jwt(self, expiry_seconds: int = settings.TOKEN_EXPIRY_SECONDS) -> str:
        """
        Generate a JWT token for the user with the specified expiry.

        Args:
            expiry_seconds (int): Number of seconds until the token expires. Defaults to settings.TOKEN_EXPIRY_SECONDS.

        Returns:
            str: Encoded JWT token as a string.

        Side Effects:
            Sets expire_day and expire_password to the expiry date string in the format 'YYYY-MM-DD HH:MM:SS'.
        """
        expiry_time = int(time.time() + expiry_seconds)
        self.expire_day = self.expire_password = datetime.fromtimestamp(expiry_time, tz=UTC).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        return jwt.encode(self.model_dump(), settings.SECRET_KEY, settings.ALGORITHM)

    @staticmethod
    def rt_jwt(auid: str, expiry_seconds: int = settings.TOKEN_EXPIRY_SECONDS) -> str:
        """
        Generate a JWT token for an RT with the specified expiry.
        """
        expiry_time = int(time.time() + expiry_seconds)
        payload = {
            "auid": auid,
            "expire_day": datetime.fromtimestamp(expiry_time, tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
        }

        return jwt.encode(payload, settings.SECRET_KEY_RT, settings.ALGORITHM)


# --- NetworkCreateRequest and related models for NBAPI network creation ---


class NmsNetworkArea(BaseModel):
    lat_deg: float = Field(default=51.5072)
    lon_deg: float = Field(default=0.1276)
    radius_km: float = Field(default=100)
    auto_parent: bool = Field(default=False)


class NmsRFDetails(BaseModel):
    freq_band: int = Field(default=39)
    upper_mhz: int = Field(default=39500)
    lower_mhz: int = Field(default=38500)
    chan_bws: list[int] = Field(default_factory=lambda: [100])


class NmsAPSystemPamSshRadius(BaseModel):
    server_ip: str = Field(default="1.2.3.4")
    server_port: int = Field(default=1234)
    shared_secret: str = Field(default="secret")
    timeout_secs: int = Field(default=5)
    source_ip: str = Field(default="4.3.2.1")
    vrf: str = Field(default="NA")


class NmsGeneralOptions(BaseModel):
    ap_system_pam_ssh_radius: NmsAPSystemPamSshRadius = Field(default_factory=NmsAPSystemPamSshRadius)


class NmsNetworkCreateRequest(BaseModel):
    name: str = Field(default="Test Network")
    details: str = Field(default="No details")
    timezone: str = Field(default="UTC")
    customer_contact_name: str = Field(default="Tester McTestface")
    customer_contact_title: str = Field(default="Tester")
    customer_contact_email: str = Field(default=f"tester@{settings.EMAIL_DOMAIN}")
    customer_contact_mobile: str = Field(default="01234567890")
    customer_contact_info: str = Field(default="N/A")
    network_area: NmsNetworkArea = Field(default_factory=NmsNetworkArea)
    rf_details: NmsRFDetails = Field(default_factory=NmsRFDetails)
    alarm_options: list[dict] = Field(default_factory=list)
    general_options: NmsGeneralOptions = Field(default_factory=NmsGeneralOptions)
    sw_version_auto_update: str | None = Field(default="")


class NmsCommonCreateRequest(BaseModel):
    id: str | None = None
    auid: str = Field(default_factory=shortuuid.uuid)
    name: str | None = None
    address: str = "None"
    node_status: str = Field(default="Planned")
    notes: str = Field(default="No notes")

    @model_validator(mode="after")
    def fill_missing_id_name(self):
        self.id = self.id or f"ID_{self.auid}"
        self.name = self.name or f"NAME_{self.auid}"
        return self


class NmsHubCreateRequest(NmsCommonCreateRequest):
    csni: str
    address: str = "None"
    lat_deg: float = Field(default_factory=lambda: 51.5072 + zero_centred_rand(settings.MAX_DIFF_DEG))
    lon_deg: float = Field(default_factory=lambda: 0.1276 + zero_centred_rand(settings.MAX_DIFF_DEG))


class NmsAPConfiguration(BaseModel):
    ap_du_beam_profile_id: int = 4
    ap_du_dlmodulation: str = "QAM64"
    ap_du_isulcaenbld: bool = True
    ap_du_maxdlmcs: int = 25
    ap_du_nssbpwr: int = 20
    ap_du_p0nominal_pucch: int = -96
    ap_du_p0nominal_pusch: int = -100
    ap_du_prachcfgidx: int = 117
    ap_du_rf_channel_centre_frequency_ghz: str = "38.0"
    ap_du_rf_channel_downstream_carrier_bandwidth_mhz: int = 200
    ap_du_rf_channel_downstream_num_carriers: int = 4
    ap_du_rf_channel_upstream_carrier_bandwidth_mhz: int = 200
    ap_du_rf_channel_upstream_num_carriers: int = 2
    ap_du_zerocorrelationzonecfg: int = 0
    ap_rc_rt_management_csr_ippdu_gateway: str = ""
    ap_rc_rt_management_rt_ippdu_gateway: str = ""
    ap_system_ssh_password: str = ""
    ap_system_ssh_user: str = ""
    frequency_band_ghz: int = 39


class NmsAPCreateRequest(NmsCommonCreateRequest):
    allocated_auid: str = "No"
    parent_auid: str
    node_priority: str = "Bronze"
    ap_system_transmitter_enabled: bool = False
    azimuth_deg: int = 0
    elevation_deg: int = 90
    height_mast_m: int = 20
    height_asl_m: int = 21
    configuration: NmsAPConfiguration = NmsAPConfiguration()


class NmsRegisterAPSecretHeaders(BaseModel):
    gnodebid: str
    secret: str


class NmsRegisterAPCandidateRequest(BaseModel):
    csi: str
    installer_key: str
    chosen_auid: str


class NmsRegisterAPCandidateHeaders(BaseModel):
    gnodebid: str
    secret: str


class NmsRTCreateRequest(NmsCommonCreateRequest):
    parent_auid: str
    node_priority: str = "Gold"
    height_mast_m: int = 20
    height_asl_m: int = 21
    # network_details: dict = Field(default_factory=lambda: {"rt_wwan_1_ipv6_address": None})
    network_details: dict = Field(default_factory=lambda: {"rt_wwan_1_ipv6_address": None})
    lat_deg: float  # Needs to be <20km from hub (AP inherits from hub)
    lon_deg: float  # Needs to be <20km from hub (AP inherits from hub)


class NmsRTRegisterParam(BaseModel):
    name: str
    type: str
    value: str


class NmsRTRegisterRequest(BaseModel):
    params: list[NmsRTRegisterParam]
