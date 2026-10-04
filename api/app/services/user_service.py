"""帳號管理"""

from sqlalchemy.orm import Session

from app.errors import BadRequestError, NotFoundError, UnprocessableError
from app.models import Department, Role, Student, StudentStatus, Teacher, UserAccount
from app.repositories import course_repository, student_repository, teacher_repository, user_repository
from app.schemas.user_schema import StudentCreateIn, TeacherCreateIn, UserCreateIn, UserUpdateIn
from app.services.auth_service import hash_password


def _get(db: Session, user_id: int) -> UserAccount:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError("找不到帳號")
    return user


def list_users(db: Session, role: Role | None, keyword: str | None) -> list[UserAccount]:
    return user_repository.list_users(db, role, keyword.strip() if keyword and keyword.strip() else None)


def create_user(db: Session, data: UserCreateIn) -> UserAccount:
    """建立帳號；教師／學生的個人資料在同一個交易內一併建立（帳號或代碼重複時由資料庫回報 409）"""
    account = UserAccount(username=data.username, password_hash=hash_password(data.password), role=Role(data.role))
    user_repository.add(db, account)
    if isinstance(data, TeacherCreateIn):
        teacher_repository.add(db, Teacher(**data.profile.model_dump(), user=account))
    elif isinstance(data, StudentCreateIn):
        student_repository.add(db, Student(**data.profile.model_dump(), status=StudentStatus.Enrolled, user=account))
    db.commit()
    return _get(db, account.user_id)


def update_user(db: Session, admin_id: int, user_id: int, data: UserUpdateIn) -> UserAccount:
    """停用／啟用、重設密碼"""
    if data.is_active is None and data.password is None:
        raise UnprocessableError("至少需提供一個欄位")
    if data.is_active is False and user_id == admin_id:
        raise BadRequestError("不可停用自己的帳號")

    user = _get(db, user_id)
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password is not None:
        user.password_hash = hash_password(data.password)
    db.commit()
    return user


def update_student_status(db: Session, student_id: str, status: str) -> Student:
    """變更學籍（休學／退學的學生不可選課）"""
    student = student_repository.get(db, student_id)
    if student is None:
        raise NotFoundError("找不到學生")
    student.status = StudentStatus(status)
    db.commit()
    return student


def list_departments(db: Session) -> list[Department]:
    return course_repository.list_departments(db)
