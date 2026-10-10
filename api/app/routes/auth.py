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
    """登入成功時寫入 cookie，並回傳使用者資訊供前端決定導向哪個角色首頁"""
    # 限流檢查放在驗證密碼之前：被擋下的請求不會進行 bcrypt 運算
    login_limiter.check(client_ip(request))
    user = auth_service.login(db, body.username, body.password)
    # 宣告 response 參數後，在其上設定的 cookie 會合併到 FastAPI 最終回傳的回應中
    set_session_cookie(response, user)
    return {"user": user.to_public()}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    """登出：刪除 cookie（不需要登入也可呼叫）"""
    clear_session_cookie(response)


@router.get("/me")
def me(user: AnyUser):
    """目前登入者（內容取自 JWT，不查資料庫）"""
    return {"user": user.to_public()}
