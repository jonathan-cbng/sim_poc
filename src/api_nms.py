import time
from datetime import UTC, datetime

import jwt
from pydantic import BaseModel, Field

from src.config import settings


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
    customer_contact_name: str = Field(default="Billy Lardner")
    customer_contact_title: str = Field(default="SE")
    customer_contact_email: str = Field(default="tester@cbng.co.uk")
    customer_contact_mobile: str = Field(default="01234567890")
    customer_contact_info: str = Field(default="N/A")
    network_area: NmsNetworkArea = Field(default_factory=NmsNetworkArea)
    rf_details: NmsRFDetails = Field(default_factory=NmsRFDetails)
    alarm_options: list[dict] = Field(default_factory=list)
    general_options: NmsGeneralOptions = Field(default_factory=NmsGeneralOptions)
    sw_version_auto_update: str | None = Field(default="")
