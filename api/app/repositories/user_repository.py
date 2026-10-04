"""帳號的資料存取（只負責查詢與新增，不判斷業務規則、不 commit）"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Role, Student, Teacher, UserAccount


def _with_profiles():
    return (selectinload(UserAccount.teacher), selectinload(UserAccount.student))


def find_by_username(db: Session, username: str) -> UserAccount | None:
    return db.scalar(select(UserAccount).where(UserAccount.username == username).options(*_with_profiles()))


def get_by_id(db: Session, user_id: int) -> UserAccount | None:
    return db.scalar(select(UserAccount).where(UserAccount.user_id == user_id).options(*_with_profiles()))


def list_users(db: Session, role: Role | None, keyword: str | None) -> list[UserAccount]:
    """依角色與關鍵字（帳號、教師姓名、學生姓名）篩選"""
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
    db.add(account)


def count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(UserAccount)) or 0
