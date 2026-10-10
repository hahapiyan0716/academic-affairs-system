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
    """從 cookie 取出 JWT 並還原登入者；參數名稱 access_token 即 cookie 名稱"""
    if not access_token:
        raise UnauthorizedError("尚未登入")
    return decode_token(access_token)


def require_role(*roles: Role):
    """產生「登入且角色屬於 roles 之一」的依賴函式"""

    def checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError("權限不足")
        return user

    return checker


# 路由參數的型別別名：AnyUser 只要求登入，其餘另外限定角色
AnyUser = Annotated[CurrentUser, Depends(get_current_user)]
AdminUser = Annotated[CurrentUser, Depends(require_role("Admin"))]
TeacherUser = Annotated[CurrentUser, Depends(require_role("Teacher"))]
StudentUser = Annotated[CurrentUser, Depends(require_role("Student"))]


def teacher_id_of(user: CurrentUser) -> str:
    """取出教師代碼；Teacher 角色的帳號理論上都有，缺少時表示帳號資料異常"""
    if not user.teacher_id:
        raise ForbiddenError("此帳號未連結教師資料")
    return user.teacher_id


def student_id_of(user: CurrentUser) -> str:
    """取出學號；Student 角色的帳號理論上都有，缺少時表示帳號資料異常"""
    if not user.student_id:
        raise ForbiddenError("此帳號未連結學生資料")
    return user.student_id
