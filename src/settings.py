from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AP-RT Management API"
    LOG_LEVEL: str = "INFO"

    NMS_HOST: str = "localhost"
    NMS_NB_PORT: int = 5000

    DEFAULT_HEARTBEAT_SECONDS: int = 30
    DEFAULT_RTS_PER_AP: int = 64


settings = Settings()
