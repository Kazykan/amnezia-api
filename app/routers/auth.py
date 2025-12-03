from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from utils.jwt import create_access_token, create_refresh_token, decode_token
from core.config import settings

router = APIRouter(tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenPair)
def login(req: LoginRequest):
    # тут должна быть проверка пользователя в БД
    if (
        req.username != settings.ADMIN_USERNAME
        or req.password != settings.ADMIN_PASSWORD
    ):
        raise HTTPException(status_code=401, detail="Неверные учетные данные")
    access = create_access_token(sub=req.username, roles=["admin"])
    refresh = create_refresh_token(sub=req.username)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
def refresh(req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Неверный тип токена")
    access = create_access_token(sub=payload["sub"], roles=payload.get("roles", []))
    new_refresh = create_refresh_token(sub=payload["sub"])
    return TokenPair(access_token=access, refresh_token=new_refresh)
