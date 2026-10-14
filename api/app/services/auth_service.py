"""登入與密碼"""

from datetime import datetime

import bcrypt
from sqlalchemy.orm import Session

from app.errors import BadRequestError, ForbiddenError, UnauthorizedError
from app.models import UserAccount
from app.repositories import user_repository
from app.schemas.auth_schema import PASSWORD_MAX_BYTES
from app.session import CurrentUser

# bcrypt 的 cost factor：雜湊需要 2^10 輪運算，數字越大越安全也越慢
BCRYPT_ROUNDS = 10


def hash_password(password: str) -> str:
    """產生 bcrypt 雜湊；salt 已包含在回傳的字串中，不必另外儲存"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """比對明碼與雜湊是否相符"""
    encoded = password.encode()     # encode() 會把字串轉成 bytes，bcrypt 只接受 bytes
    # bcrypt 5.x 對超過 72 bytes 的輸入直接拋出 ValueError；超長密碼一律視為錯誤
    if len(encoded) > PASSWORD_MAX_BYTES:
        return False
    # checkpw() 從雜湊字串（格式 $2b$<cost>$<22 字元 salt><31 字元雜湊>）取出 cost factor 與 salt，
    # 以同樣的參數雜湊明碼，再比對兩個雜湊是否相同
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
        token_version=account.token_version,
    )


def ensure_session_valid(db: Session, user: CurrentUser) -> None:
    """
    每個需要登入的請求都會呼叫：JWT 有效期間帳號仍可能被停用、刪除或變更密碼，必須以資料庫為準。
    回 401（而非 403）讓前端清除 cookie 並回到登入頁。
    """
    state = user_repository.find_session_state(db, user.user_id)
    if state is None or not state[0]:
        raise UnauthorizedError("帳號已停用或不存在，請重新登入")
    # 版本不同代表簽發此 JWT 之後密碼已被修改或重設
    if state[1] != user.token_version:
        raise UnauthorizedError("密碼已變更，請重新登入")


def set_password(account: UserAccount, password: str) -> None:
    """設定新密碼並讓所有既有的登入失效（呼叫端負責 commit）"""
    account.password_hash = hash_password(password)
    account.token_version += 1


def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> CurrentUser:
    """
    登入者修改自己的密碼；回傳新版本的身分，由 route 重新簽發 cookie，讓目前這台裝置維持登入。
    目前密碼錯誤回 400 而非 401：401 會讓前端當成登入失效而登出。
    """
    account = user_repository.get_by_id(db, user_id)
    if account is None:
        raise UnauthorizedError("帳號已停用或不存在，請重新登入")
    if not verify_password(current_password, account.password_hash):
        raise BadRequestError("目前的密碼不正確")
    if verify_password(new_password, account.password_hash):
        raise BadRequestError("新密碼不可與目前的密碼相同")
    set_password(account, new_password)
    db.commit()
    return to_current_user(account)


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
