"""登入與密碼"""

from datetime import datetime

import bcrypt
from sqlalchemy.orm import Session

from app.errors import ForbiddenError, UnauthorizedError
from app.models import UserAccount
from app.repositories import user_repository
from app.schemas.auth_schema import PASSWORD_MAX_BYTES
from app.session import CurrentUser

BCRYPT_ROUNDS = 10


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode()
    # bcrypt 5.x 對超過 72 bytes 的輸入直接拋出 ValueError；超長密碼一律視為錯誤
    if len(encoded) > PASSWORD_MAX_BYTES:
        return False
    return bcrypt.checkpw(encoded, password_hash.encode())


# 帳號不存在時仍執行一次 bcrypt 比對，讓兩種失敗的回應時間一致，避免以時間差推測帳號是否存在
DUMMY_HASH = hash_password("dummy-password-for-timing")


def to_current_user(account: UserAccount) -> CurrentUser:
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


def login(db: Session, username: str, password: str) -> CurrentUser:
    account = user_repository.find_by_username(db, username)
    ok = verify_password(password, account.password_hash if account else DUMMY_HASH)
    if account is None or not ok:
        raise UnauthorizedError("帳號或密碼錯誤")
    if not account.is_active:
        raise ForbiddenError("帳號已停用，請洽管理員")

    account.last_login_at = datetime.now()
    db.commit()
    return to_current_user(account)
