"""
認證與授權：密碼雜湊、JWT 簽發與驗證、角色檢查。

JWT 以 HS256 簽章，存放於 httpOnly cookie；Next.js 的 proxy.ts 以同一組 JWT_SECRET 驗證，只用來決定頁面導向。
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

import bcrypt
import jwt
from fastapi import Cookie, Depends, HTTPException, status

from app.config import get_settings

Role = Literal["Admin", "Teacher", "Student"]

# bcrypt 只處理前 72 bytes；bcrypt 5.x 對超過長度的輸入直接拋出 ValueError，因此在驗證層先限制
PASSWORD_MAX_BYTES = 72
BCRYPT_ROUNDS = 10


# ---------------------------------------------------------------------
# 密碼
# ---------------------------------------------------------------------


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode()
    if len(encoded) > PASSWORD_MAX_BYTES:
        return False
    return bcrypt.checkpw(encoded, password_hash.encode())


# 帳號不存在時仍執行一次 bcrypt 比對，避免以回應時間差推測帳號是否存在
DUMMY_HASH = hash_password("dummy-password-for-timing")


# ---------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class CurrentUser:
    """
    JWT 內容。刻意不放 can_open_section 與學籍狀態：
    權限可能隨時被管理員收回，必須每次查資料庫確認。
    """

    user_id: int
    username: str
    role: Role
    name: str
    teacher_id: str | None
    student_id: str | None

    def to_public(self) -> dict[str, Any]:
        """回傳給前端的格式（sub 為字串，與 JWT 的 sub 一致）"""
        return {
            "sub": str(self.user_id),
            "username": self.username,
            "role": self.role,
            "name": self.name,
            "teacher_id": self.teacher_id,
            "student_id": self.student_id,
        }


def create_token(user: CurrentUser) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        **user.to_public(),
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expires_in_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def get_current_user(access_token: Annotated[str | None, Cookie()] = None) -> CurrentUser:
    if not access_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "尚未登入")
    settings = get_settings()
    try:
        payload = jwt.decode(
            access_token,
            settings.jwt_secret,
            algorithms=["HS256"],  # 明確限定演算法，防止 alg=none 或演算法替換攻擊
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iss", "sub"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登入已失效，請重新登入") from None

    return CurrentUser(
        user_id=int(payload["sub"]),
        username=payload["username"],
        role=payload["role"],
        name=payload.get("name", ""),
        teacher_id=payload.get("teacher_id"),
        student_id=payload.get("student_id"),
    )


def require_role(*roles: Role):
    def checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "權限不足")
        return user

    return checker


AnyUser = Annotated[CurrentUser, Depends(get_current_user)]
AdminUser = Annotated[CurrentUser, Depends(require_role("Admin"))]
TeacherUser = Annotated[CurrentUser, Depends(require_role("Teacher"))]
StudentUser = Annotated[CurrentUser, Depends(require_role("Student"))]
