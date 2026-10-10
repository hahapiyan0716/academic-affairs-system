"""帳號的資料存取（只負責查詢與新增，不判斷業務規則、不 commit）"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Role, Student, Teacher, UserAccount


def _with_profiles():
    """預先載入帳號對應的教師／學生資料，避免 N+1 查詢"""
    return (selectinload(UserAccount.teacher), selectinload(UserAccount.student))


def find_by_username(db: Session, username: str) -> UserAccount | None:
    """依帳號名稱查詢（登入、檢查帳號重複時使用）"""
    return db.scalar(select(UserAccount).where(UserAccount.username == username).options(*_with_profiles()))


def get_by_id(db: Session, user_id: int) -> UserAccount | None:
    """依 user_id 取得帳號，一併載入教師／學生資料"""
    return db.scalar(select(UserAccount).where(UserAccount.user_id == user_id).options(*_with_profiles()))


def find_is_active(db: Session, user_id: int) -> bool | None:
    """只查帳號的啟用狀態（以主鍵查單一欄位）；帳號不存在時回傳 None"""
    return db.scalar(select(UserAccount.is_active).where(UserAccount.user_id == user_id))


def list_users(db: Session, role: Role | None, keyword: str | None) -> list[UserAccount]:
    """依角色與關鍵字（帳號、教師姓名、學生姓名）篩選"""
    # 以 LEFT JOIN 接上教師與學生：Admin 兩邊都沒有，仍要出現在結果中
    stmt = (
        select(UserAccount)
        .outerjoin(Teacher, Teacher.user_id == UserAccount.user_id)
        .outerjoin(Student, Student.user_id == UserAccount.user_id)
        .options(*_with_profiles())
        .order_by(UserAccount.role, UserAccount.username)
    )
    if role:
        stmt = stmt.where(UserAccount.role == role)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(UserAccount.username.like(like), Teacher.teacher_name.like(like), Student.student_name.like(like))
        )
    return list(db.scalars(stmt))


def add(db: Session, account: UserAccount) -> None:
    """加入 Session；實際寫入在 service commit 時"""
    db.add(account)


def count(db: Session) -> int:
    """帳號總數"""
    return db.scalar(select(func.count()).select_from(UserAccount)) or 0
