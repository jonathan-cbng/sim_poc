import time
from datetime import UTC, datetime

import jwt
from pydantic import BaseModel, Field

from src.config import settings


# --- Network Creation ---
class NetworkArea(BaseModel):
    lat_deg: float
    lon_deg: float
    radius_km: float
    auto_parent: bool


class RFDetails(BaseModel):
    freq_band: int
    upper_mhz: int
    lower_mhz: int
    chan_bws: list[int]


class APSystemPamSshRadius(BaseModel):
    server_ip: str
    server_port: int
    shared_secret: str
    timeout_secs: int
    source_ip: str
    vrf: str


class GeneralOptions(BaseModel):
    ap_system_pam_ssh_radius: APSystemPamSshRadius


class NetworkCreateRequest(BaseModel):
    name: str
    details: str
    timezone: str
    customer_contact_name: str
    customer_contact_title: str
    customer_contact_email: str
    customer_contact_mobile: str
    customer_contact_info: str
    network_area: NetworkArea
    rf_details: RFDetails
    alarm_options: list = Field(default_factory=list)
    general_options: GeneralOptions
    sw_version_auto_update: str


# --- Hub Creation ---
class HubCreateRequest(BaseModel):
    csni: str
    auid: str
    id: str
    name: str
    address: str
    lat_deg: float
    lon_deg: float
    node_status: str
    notes: str


# --- AP Creation ---
class APConfiguration(BaseModel):
    ap_du_beam_profile_id: int
    ap_du_dlmodulation: str
    ap_du_isulcaenbld: bool
    ap_du_maxdlmcs: int
    ap_du_nssbpwr: int
    ap_du_p0nominal_pucch: int
    ap_du_p0nominal_pusch: int
    ap_du_prachcfgidx: int
    ap_du_rf_channel_centre_frequency_ghz: str
    ap_du_rf_channel_downstream_carrier_bandwidth_mhz: int
    ap_du_rf_channel_downstream_num_carriers: int
    ap_du_rf_channel_upstream_carrier_bandwidth_mhz: int
    ap_du_rf_channel_upstream_num_carriers: int
    ap_du_zerocorrelationzonecfg: int
    ap_rc_rt_management_csr_ippdu_gateway: str
    ap_rc_rt_management_rt_ippdu_gateway: str
    ap_system_ssh_password: str
    ap_system_ssh_user: str
    frequency_band_ghz: int


class APCreateRequest(BaseModel):
    auid: str
    allocated_auid: str
    id: str
    name: str
    parent_auid: str
    node_status: str
    node_priority: str
    ap_system_transmitter_enabled: bool
    azimuth_deg: int
    elevation_deg: int
    height_mast_m: int
    height_asl_m: int
    notes: str
    configuration: APConfiguration


# --- AP Secret Registration ---
class APRegisterSecretRequest(BaseModel):
    pass  # Body is empty, only headers are used


# --- AP Candidate Registration ---
class APRegisterCandidateRequest(BaseModel):
    csi: str
    installer_key: str
    chosen_auid: str


# --- RT Creation ---
class RTNetworkDetails(BaseModel):
    rt_wwan_1_ipv6_address: str | None = None


class RTCreateRequest(BaseModel):
    auid: str
    id: str
    name: str
    parent_auid: str
    node_priority: str
    node_status: str
    address: str
    lat_deg: float
    lon_deg: float
    height_mast_m: int
    height_asl_m: int
    notes: str
    network_details: RTNetworkDetails


# --- RT Registration ---
class RTRegistrationParam(BaseModel):
    name: str
    type: str
    value: str


class RTRegisterRequest(BaseModel):
    params: list[RTRegistrationParam]


class AuthInfo(BaseModel):
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
