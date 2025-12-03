import time, jwt
from typing import Dict, Any
from core.config import settings


def _now() -> int:
    return int(time.time())


def create_access_token(sub: str, roles: list[str] | None = None) -> str:
    now = _now()
    payload = {
        "sub": sub,
        "iat": now,
        "nbf": now - 5,
        "exp": now + settings.JWT_ACCESS_TTL,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "access",
        "roles": roles or [],
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(sub: str) -> str:
    now = _now()
    payload = {
        "sub": sub,
        "iat": now,
        "nbf": now - 5,
        "exp": now + settings.JWT_REFRESH_TTL,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )
