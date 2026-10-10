"""登入與密碼"""

from datetime import datetime

import bcrypt
from sqlalchemy.orm import Session

from app.errors import ForbiddenError, UnauthorizedError
from app.models import UserAccount
from app.repositories import user_repository
from app.schemas.auth_schema import PASSWORD_MAX_BYTES
from app.session import CurrentUser

# bcrypt 的 cost factor：雜湊需要 2^10 輪運算，數字越大越安全也越慢
BCRYPT_ROUNDS = 10


def hash_password(password: str) -> str:
    """產生 bcrypt 雜湊；鹽值（salt）已包含在回傳的字串中，不必另外儲存"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """比對明碼與雜湊是否相符"""
    encoded = password.encode()
    # bcrypt 5.x 對超過 72 bytes 的輸入直接拋出 ValueError；超長密碼一律視為錯誤
    if len(encoded) > PASSWORD_MAX_BYTES:
        return False
    return bcrypt.checkpw(encoded, password_hash.encode())


# 帳號不存在時仍執行一次 bcrypt 比對，讓兩種失敗的回應時間一致，避免以時間差推測帳號是否存在
DUMMY_HASH = hash_password("dummy-password-for-timing")


def to_current_user(account: UserAccount) -> CurrentUser:
    """帳號 → JWT 內的登入者身分；顯示名稱取自教師或學生資料，Admin 使用固定名稱"""
    if account.teacher:
        name = account.teacher.teacher_name
    elif account.student:
        name = account.student.student_name
    else:
        name = "系統管理員"
    return CurrentUser(
        user_id=account.user_id,
        username=account.username,
        role=account.role.value,  # type: ignore[arg-type]
        name=name,
        teacher_id=account.teacher.teacher_id if account.teacher else None,
        student_id=account.student.student_id if account.student else None,
    )


def ensure_active(db: Session, user_id: int) -> None:
    """
    每個需要登入的請求都會呼叫：JWT 有效期間帳號仍可能被停用或刪除，必須以資料庫為準。
    回 401（而非 403）讓前端清除 cookie 並回到登入頁。
    """
    if not user_repository.find_is_active(db, user_id):
        raise UnauthorizedError("帳號已停用或不存在，請重新登入")


def login(db: Session, username: str, password: str) -> CurrentUser:
    """驗證帳號密碼並記錄登入時間；成功時回傳登入者身分，由 route 寫入 cookie"""
    account = user_repository.find_by_username(db, username)
    ok = verify_password(password, account.password_hash if account else DUMMY_HASH)
    # 帳號不存在與密碼錯誤回傳相同訊息，不透露帳號是否存在
    if account is None or not ok:
        raise UnauthorizedError("帳號或密碼錯誤")
    # 密碼正確後才檢查停用狀態，避免未知密碼者藉此探測帳號
    if not account.is_active:
        raise ForbiddenError("帳號已停用，請洽管理員")

    account.last_login_at = datetime.now()
    db.commit()
    return to_current_user(account)
