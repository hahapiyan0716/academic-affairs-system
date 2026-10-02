"""
認證：驗證 Express 簽發、存放於 httpOnly cookie 的 JWT。
FastAPI 不負責登入，只負責「驗證」與「授權」。
"""

from dataclasses import dataclass
from typing import Annotated, Literal

import jwt
from fastapi import Cookie, Depends, HTTPException, status

from app.config import get_settings

Role = Literal["Admin", "Teacher", "Student"]


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    username: str
    role: Role
    name: str
    teacher_id: str | None
    student_id: str | None


def get_current_user(access_token: Annotated[str | None, Cookie()] = None) -> CurrentUser:
    if not access_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "尚未登入")
    settings = get_settings()
    try:
        payload = jwt.decode(
            access_token,
            settings.jwt_secret,
            algorithms=["HS256"],  # 明確限定演算法，與 Express 端一致
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
TeacherUser = Annotated[CurrentUser, Depends(require_role("Teacher"))]
StudentUser = Annotated[CurrentUser, Depends(require_role("Student"))]
