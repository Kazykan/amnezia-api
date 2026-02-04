from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from utils.jwt import decode_token
from core.config import settings

bearer_scheme = HTTPBearer()


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    # --- TEST MODE: авторизация отключена ---
    if getattr(settings, "TEST_MODE", False):
        return {
            "sub": "test-user",
            "roles": ["admin"],
            "type": "access",
        }

    # --- Обычный режим ---
    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или просроченный токен",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный тип токена",
        )

    return payload
