"""學期的資料存取"""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Section, Semester


def get(db: Session, semester_id: str) -> Semester | None:
    return db.get(Semester, semester_id)


def get_current(db: Session) -> Semester | None:
    return db.scalar(select(Semester).where(Semester.is_current.is_(True)))


def list_all(db: Session) -> list[Semester]:
    return list(db.scalars(select(Semester).order_by(Semester.semester_id.desc())))


def add(db: Session, semester: Semester) -> None:
    db.add(semester)


def clear_current_except(db: Session, semester_id: str) -> None:
    db.execute(update(Semester).where(Semester.semester_id != semester_id).values(is_current=False))


def section_counts(db: Session, semester_ids: list[str]) -> dict[str, int]:
    """各學期的開班數"""
    if not semester_ids:
        return {}
    rows = db.execute(
        select(Section.semester_id, func.count())
        .where(Section.semester_id.in_(semester_ids))
        .group_by(Section.semester_id)
    ).all()
    return {semester_id: n for semester_id, n in rows}
