import os


class Settings:
    JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TTL = int(os.getenv("JWT_ACCESS_TTL", "900"))  # 15 минут
    JWT_REFRESH_TTL = int(os.getenv("JWT_REFRESH_TTL", "1209600"))  # 14 дней
    JWT_ISSUER = os.getenv("JWT_ISSUER", "amnezia-api")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "amnezia-clients")

    # логин и пароль для авторизации
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")


settings = Settings()
