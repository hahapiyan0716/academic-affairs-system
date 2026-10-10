"""課程庫的資料存取"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Course, CurriculumField, Department, Section


def _with_details():
    """
    預先載入領域與系所的選項。selectinload 以額外一句 IN 查詢一次取回所有課程的關聯資料，
    避免逐筆存取 course.fields 時產生 N+1 查詢
    """
    return (selectinload(Course.fields), selectinload(Course.department))


def get(db: Session, course_no: str) -> Course | None:
    """依主鍵取得課程，不存在回傳 None"""
    return db.get(Course, course_no)


def get_with_details(db: Session, course_no: str) -> Course | None:
    """一併載入領域與系所"""
    return db.scalar(select(Course).where(Course.course_no == course_no).options(*_with_details()))


def list_with_details(db: Session) -> list[Course]:
    """全部課程（含停用），一併載入領域與系所"""
    return list(db.scalars(select(Course).options(*_with_details()).order_by(Course.course_no)))


def list_active(db: Session) -> list[Course]:
    """啟用中的課程（可開新班者）"""
    return list(db.scalars(select(Course).where(Course.is_active.is_(True)).order_by(Course.course_no)))


def list_field_names(db: Session) -> list[str]:
    """所有出現過的課程領域（不重複）"""
    return list(db.scalars(select(CurriculumField.field_name).distinct().order_by(CurriculumField.field_name)))


def add(db: Session, course: Course) -> None:
    """加入 Session；實際寫入在 service commit 時"""
    db.add(course)


def count_active(db: Session) -> int:
    """啟用中的課程數"""
    return db.scalar(select(func.count()).select_from(Course).where(Course.is_active.is_(True))) or 0


def section_counts(db: Session, course_nos: list[str]) -> dict[str, int]:
    """各課程的歷年開班次數"""
    if not course_nos:
        return {}
    rows = db.execute(
        select(Section.course_no, func.count()).where(Section.course_no.in_(course_nos)).group_by(Section.course_no)
    ).all()
    return {course_no: n for course_no, n in rows}


def list_departments(db: Session) -> list[Department]:
    """全部系所，依系所代碼排序"""
    return list(db.scalars(select(Department).order_by(Department.dept_id)))
