"""學生的資料存取"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Student, StudentStatus


def get(db: Session, student_id: str) -> Student | None:
    return db.get(Student, student_id)


def lock(db: Session, student_id: str) -> Student | None:
    """SELECT ... FOR UPDATE：讓同一位學生的加退選請求依序執行"""
    return db.scalar(select(Student).where(Student.student_id == student_id).with_for_update())


def add(db: Session, student: Student) -> None:
    db.add(student)


def count_enrolled(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Student).where(Student.status == StudentStatus.Enrolled)) or 0
