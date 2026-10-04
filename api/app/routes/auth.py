"""認證 API：登入（簽發 JWT 並寫入 httpOnly cookie）、登出、目前使用者"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.middleware.rate_limit import client_ip, login_limiter
from app.middleware.require_auth import AnyUser
from app.schemas.auth_schema import LoginIn
from app.services import auth_service
from app.session import clear_session_cookie, set_session_cookie

router = APIRouter(prefix="/api/auth", tags=["auth"])

DB = Annotated[Session, Depends(get_db)]


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: DB):
    login_limiter.check(client_ip(request))
    user = auth_service.login(db, body.username, body.password)
    set_session_cookie(response, user)
    return {"user": user.to_public()}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    clear_session_cookie(response)


@router.get("/me")
def me(user: AnyUser):
    return {"user": user.to_public()}
