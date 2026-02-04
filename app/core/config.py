from pydantic_settings import BaseSettings
from pydantic import BaseModel


class BlockIPRequest(BaseModel):
    ip: str


class BlockClientRequest(BaseModel):
    client_name: str
    ip: str


class Settings(BaseSettings):
    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TTL: int = 900
    JWT_REFRESH_TTL: int = 1209600
    JWT_ISSUER: str = "amnezia-api"
    JWT_AUDIENCE: str = "amnezia-clients"

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "1234"

    # AWG / Docker
    ENDPOINT: str
    WG_CONFIG_FILE: str
    DOCKER_CONTAINER: str
    DOCKER_BIN: str = "/usr/bin/docker"
    CLIENTS_TABLE_PATH: str = "/opt/amnezia/awg/clientsTable"

    # Test mode (отключает авторизацию)
    TEST_MODE: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore
