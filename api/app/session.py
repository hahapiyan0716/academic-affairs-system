"""
登入狀態：JWT 的簽發、驗證與 cookie 屬性。

JWT 以 HS256 簽章，存放於 httpOnly cookie；Next.js 的 proxy.ts 以同一組 JWT_SECRET 驗證，只用來決定頁面導向。
JWT 刻意不放 can_open_section 與學籍狀態：權限可能隨時被管理員收回，必須每次查資料庫確認。
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from fastapi import Response

from app.config import get_settings
from app.errors import UnauthorizedError

# Role 是型別別名：把 Literal["Admin", "Teacher", "Student"] 取名為 Role，
# CurrentUser、require_role() 等處寫 role: Role 即可，不必重複列出三個值。
# Literal 表示「值只能是列出的其中之一」，type checker（Pylance）會在開發階段抓出錯字或無效角色；
# 但它不做執行期驗證（CurrentUser 是 dataclass，不會檢查）。執行時的保障是：decode_token() 驗證 JWT 簽章，
# 確保 role 是本系統簽發、未被竄改；require_role() 再檢查該角色能否呼叫該 API。
Role = Literal["Admin", "Teacher", "Student"]

# frozen=True 禁止 CurrentUser 建立後重新指定欄位，避免請求處理期間意外改動已驗證的登入身分。
# 它不負責防止 JWT 被竄改；JWT 的完整性由下方 decode_token() 的簽章驗證保障。
# 若執行 user.username = "root"，dataclasses 會拋出 FrozenInstanceError。
@dataclass(frozen=True)
class CurrentUser:
    """從 JWT 解出的登入者身分；teacher_id / student_id 只有對應角色才有值"""

    user_id: int
    username: str
    role: Role
    name: str
    teacher_id: str | None
    student_id: str | None
    # 簽發 JWT 當下的 UserAccount.token_version；只放在 JWT（ver），不回傳給前端
    token_version: int = 0

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
    """簽發 JWT：payload 為登入者身分加上 ver（登入狀態版本）、iss（簽發者）、iat（簽發時間）、exp（到期時間）"""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        **user.to_public(),
        "ver": user.token_version,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expires_in_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> CurrentUser:
    """驗證簽章、簽發者與到期時間後還原登入者；任何一項不符都視為未登入"""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],  # 明確限定演算法，防止 alg=none 或演算法替換攻擊
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iss", "sub"]},
        )
    except jwt.PyJWTError:
        raise UnauthorizedError("登入已失效，請重新登入") from None

    return CurrentUser(
        user_id=int(payload["sub"]),
        username=payload["username"],
        role=payload["role"],
        name=payload.get("name", ""),
        teacher_id=payload.get("teacher_id"),
        student_id=payload.get("student_id"),
        # 加入 ver 之前簽發的 JWT 沒有此欄位，視為版本 0（與既有帳號的預設值一致）
        token_version=payload.get("ver", 0),
    )


def set_session_cookie(response: Response, user: CurrentUser) -> None:
    """登入成功時寫入 JWT cookie；cookie 效期與 JWT 效期一致"""
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


def clear_session_cookie(response: Response) -> None:
    """登出：刪除 cookie（path 必須與寫入時相同，瀏覽器才會刪到同一個 cookie）"""
    response.delete_cookie(get_settings().auth_cookie, path="/")
