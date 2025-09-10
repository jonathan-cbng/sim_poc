from pydantic_core import Url
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_PORT: int = 12500
    APP_HOST: str = "0.0.0.0"
    APP_NAME: str = "AP-RT Management API"
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    NMS_URL: Url = "http://localhost"
    NBAPI_PORT: int = 5080
    SBAPI_PORT: int = 6080

    NBAPI_URL: str = f"{NMS_URL}:{NBAPI_PORT}"
    SBAPI_URL: str = f"{NMS_URL}:{SBAPI_PORT}"

    SSL_CERT: str | None = None

    DEFAULT_HEARTBEAT_SECONDS: int = 30
    DEFAULT_HUBS_PER_NETWORK: int = 2
    DEFAULT_APS_PER_HUB: int = 10
    DEFAULT_RTS_PER_AP: int = 64

    PUB_PORT: int = 12501  # Port for publishing commands to AP simulators
    PULL_PORT: int = 12502  # Port for receiving messages from AP simulators

    SECRET_KEY: str = "Hello"
    ALGORITHM: str = "HS256"

    TOKEN_EXPIRY_SECONDS: int = 3600 * 24  # 1 day


settings = Settings()
