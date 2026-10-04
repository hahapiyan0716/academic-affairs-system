"""教師與開課權限稽核的資料存取"""

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session, selectinload

from app.models import Section, SectionSchedule, SectionStatus, SectionTeacher, Teacher, TeacherPermissionLog


def get(db: Session, teacher_id: str, *, lock: bool = False) -> Teacher | None:
    return db.get(Teacher, teacher_id, with_for_update=lock)


def add(db: Session, teacher: Teacher) -> None:
    db.add(teacher)


def list_brief(db: Session) -> list[Teacher]:
    return list(db.scalars(select(Teacher).order_by(Teacher.teacher_id)))


def list_with_permission_logs(db: Session) -> list[Teacher]:
    """教師列表，一併載入登入帳號與權限異動紀錄（依時間由新到舊）"""
    return list(
        db.scalars(
            select(Teacher)
            .options(
                selectinload(Teacher.user),
                selectinload(Teacher.permission_logs).selectinload(TeacherPermissionLog.admin),
            )
            .order_by(Teacher.teacher_id)
        )
    )


def find_existing_ids(db: Session, teacher_ids: list[str]) -> set[str]:
    return set(db.scalars(select(Teacher.teacher_id).where(Teacher.teacher_id.in_(teacher_ids))))


def count_with_permission(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Teacher).where(Teacher.can_open_section.is_(True))) or 0


def add_permission_log(db: Session, log: TeacherPermissionLog) -> None:
    db.add(log)


def list_permission_logs(db: Session, teacher_id: str) -> list[TeacherPermissionLog]:
    return list(
        db.scalars(
            select(TeacherPermissionLog)
            .where(TeacherPermissionLog.teacher_id == teacher_id)
            .options(selectinload(TeacherPermissionLog.admin))
            .order_by(TeacherPermissionLog.changed_at.desc(), TeacherPermissionLog.log_id.desc())
        )
    )


def find_busy_slot(
    db: Session, teacher_ids: list[str], semester_id: str, slots: list[tuple[int, int]]
) -> tuple[str, int, int] | None:
    """任一教師在同學期、同時段已有開放中的班 → 回傳（教師姓名, 星期, 節次）"""
    row = db.execute(
        select(Teacher.teacher_name, SectionSchedule.weekday, SectionSchedule.period)
        .join(SectionTeacher, SectionTeacher.section_id == SectionSchedule.section_id)
        .join(Teacher, Teacher.teacher_id == SectionTeacher.teacher_id)
        .join(Section, Section.section_id == SectionSchedule.section_id)
        .where(
            SectionTeacher.teacher_id.in_(teacher_ids),
            SectionSchedule.semester_id == semester_id,
            Section.status == SectionStatus.Open,
            tuple_(SectionSchedule.weekday, SectionSchedule.period).in_(slots),
        )
    ).first()
    return tuple(row) if row else None  # type: ignore[return-value]
