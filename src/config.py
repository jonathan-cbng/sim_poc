"""
Configuration settings for the NMS network simulator and API services.
"""

#######################################################################################################################
# Imports
#######################################################################################################################
from pydantic import Field
from pydantic_core import Url
from pydantic_settings import BaseSettings

#######################################################################################################################
# Globals
#######################################################################################################################


class Settings(BaseSettings):
    """
    Application and API configuration settings.
    """

    APP_PORT: int = Field(12500, description="Port for the API server")
    APP_HOST: str = Field("0.0.0.0", description="Host for the API server")

    LOG_LEVEL: str = Field("INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL")

    NMS_URL: Url = Field("http://localhost", description="Base URL for the NMS")
    NBAPI_PORT: int = Field(5080, description="Northbound API port")
    SBAPI_PORT: int = Field(6080, description="Southbound API port")

    NBAPI_URL: str = Field(default_factory=lambda: "http://localhost:5080", description="Full Northbound API URL")
    SBAPI_URL: str = Field(default_factory=lambda: "https://localhost:6080", description="Full Southbound API URL")

    SSL_CERT: str | None = Field(None, description="Path to SSL certificate, if any")

    DEFAULT_HEARTBEAT_SECONDS: int = Field(30, description="Default heartbeat interval")

    # 75 hubs would give 75*32*64 = 153600 RTs, which is the maximum expected network size
    DEFAULT_HUBS_PER_NETWORK: int = Field(1, description="Default number of hubs per network")
    DEFAULT_APS_PER_HUB: int = Field(32, description="Default number of APs per hub")
    DEFAULT_RTS_PER_AP: int = Field(64, description="Default number of RTs per AP")

    PUB_PORT: int = Field(12501, description="Port for publishing commands to AP simulators")
    PULL_PORT: int = Field(12502, description="Port for receiving messages from AP simulators")

    SECRET_KEY: str = Field("Hello", description="Secret key for authentication")
    SECRET_KEY_RT: str = Field("Hello", description="Secret key for RT authentication")
    ALGORITHM: str = Field("HS256", description="Algorithm for token encoding")

    TOKEN_EXPIRY_SECONDS: int = Field(3600 * 24, description="Token expiry in seconds (1 day)")

    MAX_DIFF_DEG: float = Field(0.4, description="Maximum degree difference for randomizing lat/lon")

    CSI: str = Field("CBNG001", description="Default customer ID")
    EMAIL_DOMAIN: str = Field("cbng.co.uk", description="Default email domain")

    AP_SECRET: str = Field("ap-secret", description="Default AP secret for registration")
    INSTALLER_KEY: str = Field(
        "secret", description="Installer key for authentication. Should match one from the customer db entry"
    )
    VERIFY_SSL_CERT: bool = Field(False, description="Whether to verify SSL certificates")

    HTTPX_TIMEOUT: int = Field(10, description="Timeout for HTTPX requests in seconds")

    MAX_CONCURRENT_WORKER_COMMANDS: int = Field(1, description="Maximum concurrent requests a worker can handle")


settings = Settings()  # Load settings from environment variables or .env file if present'

#######################################################################################################################
# End of file
#######################################################################################################################
