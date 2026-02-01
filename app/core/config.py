from pydantic_settings import BaseSettings


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
    CLIENTS_TABLE_PATH: str = "/opt/amnezia/awg/clientsTable"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore
