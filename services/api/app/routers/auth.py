"""認證 API：登入（簽發 JWT 並寫入 httpOnly cookie）、登出、目前使用者"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db import get_db
from app.models import UserAccount
from app.rate_limit import client_ip, login_limiter
from app.schemas_admin import LoginIn
from app.security import DUMMY_HASH, AnyUser, CurrentUser, create_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

DB = Annotated[Session, Depends(get_db)]


def _session_user(account: UserAccount) -> CurrentUser:
    return CurrentUser(
        user_id=account.user_id,
        username=account.username,
        role=account.role.value,  # type: ignore[arg-type]
        name=(
            account.teacher.teacher_name
            if account.teacher
            else account.student.student_name
            if account.student
            else "系統管理員"
        ),
        teacher_id=account.teacher.teacher_id if account.teacher else None,
        student_id=account.student.student_id if account.student else None,
    )


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: DB):
    login_limiter.check(client_ip(request))

    account = db.scalar(
        select(UserAccount)
        .where(UserAccount.username == body.username)
        .options(selectinload(UserAccount.teacher), selectinload(UserAccount.student))
    )
    # 帳號不存在時也比對一次假雜湊，讓兩種失敗的回應時間一致，避免帳號列舉
    ok = verify_password(body.password, account.password_hash if account else DUMMY_HASH)
    if account is None or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "帳號或密碼錯誤")
    if not account.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "帳號已停用，請洽管理員")

    account.last_login_at = datetime.now()
    db.commit()

    user = _session_user(account)
    settings = get_settings()
    response.set_cookie(
        settings.auth_cookie,
        create_token(user),
        max_age=settings.jwt_expires_in_hours * 3600,
        httponly=True,  # JavaScript 讀不到，防止 XSS 竊取 token
        samesite="lax",  # 跨站發起的寫入請求不會帶上 cookie，降低 CSRF 風險
        secure=settings.cookie_secure,
        path="/",
    )
    return {"user": user.to_public()}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(get_settings().auth_cookie, path="/")


@router.get("/me")
def me(user: AnyUser):
    return {"user": user.to_public()}
