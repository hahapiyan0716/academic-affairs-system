"""
認證與授權檢查（FastAPI 依賴）。

FastAPI 以「依賴（Depends）」實作每支 API 的前置檢查，作用等同 Express 的 route middleware：
在路由參數宣告 AdminUser／TeacherUser／StudentUser，就會先驗證 cookie 中的 JWT 與角色。
"""

from typing import Annotated

from fastapi import Cookie, Depends

from app.errors import ForbiddenError, UnauthorizedError
from app.session import CurrentUser, Role, decode_token


def get_current_user(access_token: Annotated[str | None, Cookie()] = None) -> CurrentUser:
    if not access_token:
        raise UnauthorizedError("尚未登入")
    return decode_token(access_token)


def require_role(*roles: Role):
    def checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError("權限不足")
        return user

    return checker


AnyUser = Annotated[CurrentUser, Depends(get_current_user)]
AdminUser = Annotated[CurrentUser, Depends(require_role("Admin"))]
TeacherUser = Annotated[CurrentUser, Depends(require_role("Teacher"))]
StudentUser = Annotated[CurrentUser, Depends(require_role("Student"))]


def teacher_id_of(user: CurrentUser) -> str:
    if not user.teacher_id:
        raise ForbiddenError("此帳號未連結教師資料")
    return user.teacher_id


def student_id_of(user: CurrentUser) -> str:
    if not user.student_id:
        raise ForbiddenError("此帳號未連結學生資料")
    return user.student_id
