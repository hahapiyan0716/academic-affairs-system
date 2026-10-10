"""開課班級的資料存取（含 v_section_detail 的查詢）"""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    ACTIVE_ENROLLMENT,
    CurriculumField,
    Enrollment,
    Section,
    SectionDetailView,
    SectionSchedule,
    SectionTeacher,
)


def _has_field(field: str) -> ColumnElement[bool]:
    """
    班級的課程屬於指定領域（精確比對，不用 field_names LIKE，避免「資料」誤中「資料科學」）。對應 SQL：
      EXISTS (SELECT 1 FROM CurriculumField cf WHERE cf.course_no = v.course_no AND cf.field_name = :field)
    """
    return exists().where(
        CurriculumField.course_no == SectionDetailView.course_no, CurriculumField.field_name == field
    )


def get_detail(db: Session, section_id: int) -> SectionDetailView | None:
    """從 v_section_detail 取得單一班級的明細"""
    return db.get(SectionDetailView, section_id)


def lock(db: Session, section_id: int) -> Section | None:
    """SELECT ... FOR UPDATE：讓搶同一個班的加退選請求依序執行"""
    return db.scalar(select(Section).where(Section.section_id == section_id).with_for_update())


def get_owned(db: Session, teacher_id: str, section_id: int, *, lock: bool = False) -> Section | None:
    """教師有授課（含合授）的班級；不是自己的班回傳 None"""
    stmt = (
        select(Section)
        .join(SectionTeacher, SectionTeacher.section_id == Section.section_id)
        .where(Section.section_id == section_id, SectionTeacher.teacher_id == teacher_id)
    )
    if lock:
        # of=Section：只鎖 Section 列，不鎖 JOIN 進來的 SectionTeacher
        stmt = stmt.with_for_update(of=Section)
    return db.scalar(stmt)


def add(db: Session, section: Section) -> None:
    """加入 Session；實際寫入在 service commit 時"""
    db.add(section)


def count(db: Session, semester_id: str) -> int:
    """某學期的班級數（含已停開）"""
    return db.scalar(select(func.count()).select_from(Section).where(Section.semester_id == semester_id)) or 0


def list_open_details(
    db: Session, semester_id: str, keyword: str | None, field: str | None = None
) -> list[SectionDetailView]:
    """某學期開放中的班級，可依課名、課號、教師姓名搜尋，並依課程領域篩選"""
    stmt = select(SectionDetailView).where(
        SectionDetailView.semester_id == semester_id,
        SectionDetailView.status == "Open",
    )
    if keyword:
        # LIKE 的值以參數綁定傳入，不會造成 SQL Injection
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                SectionDetailView.course_name.like(like),
                SectionDetailView.course_no.like(like),
                SectionDetailView.teacher_names.like(like),
            )
        )
    if field:
        stmt = stmt.where(_has_field(field))
    return list(db.scalars(stmt.order_by(SectionDetailView.course_no, SectionDetailView.section_code)))


def list_teacher_details(db: Session, teacher_id: str, semester_id: str | None) -> list[SectionDetailView]:
    """教師授課（含合授）的班級，不指定學期則列出歷年全部"""
    stmt = (
        select(SectionDetailView)
        .join(SectionTeacher, SectionTeacher.section_id == SectionDetailView.section_id)
        .where(SectionTeacher.teacher_id == teacher_id)
    )
    if semester_id:
        stmt = stmt.where(SectionDetailView.semester_id == semester_id)
    return list(db.scalars(stmt.order_by(SectionDetailView.semester_id.desc(), SectionDetailView.course_no)))


def list_history(
    db: Session,
    course_no: str | None,
    teacher: str | None,
    keyword: str | None,
    field: str | None = None,
    limit: int = 500,
) -> list[tuple[SectionDetailView, Decimal | None]]:
    """
    歷年開課紀錄與平均成績。平均成績以相關子查詢計算，對應 SQL：
      SELECT v.*, (SELECT ROUND(AVG(e.score), 1) FROM Enrollment e
                    WHERE e.section_id = v.section_id AND e.status IN ('Selected','Manual')) AS avg_score
        FROM v_section_detail v ...
    """
    avg_score = (
        select(func.round(func.avg(Enrollment.score), 1))
        .where(Enrollment.section_id == SectionDetailView.section_id, Enrollment.status.in_(ACTIVE_ENROLLMENT))
        # correlate：子查詢中的 SectionDetailView 指向外層查詢的那一列，而不是另外 FROM 一次
        .correlate(SectionDetailView)
        .scalar_subquery()
    )
    stmt = select(SectionDetailView, avg_score.label("avg_score"))
    if course_no:
        stmt = stmt.where(SectionDetailView.course_no == course_no)
    if teacher:
        stmt = stmt.where(SectionDetailView.teacher_names.like(f"%{teacher}%"))
    if keyword:
        stmt = stmt.where(
            or_(SectionDetailView.course_name.like(f"%{keyword}%"), SectionDetailView.course_no.like(f"%{keyword}%"))
        )
    if field:
        stmt = stmt.where(_has_field(field))
    rows = db.execute(stmt.order_by(SectionDetailView.semester_id.desc(), SectionDetailView.course_no).limit(limit))
    return [(view, avg) for view, avg in rows]


def slots_by_section(db: Session, semester_id: str) -> dict[int, set[tuple[int, int]]]:
    """某學期每個班級佔用的（星期, 節次）"""
    slots: dict[int, set[tuple[int, int]]] = defaultdict(set)
    for section_id, weekday, period in db.execute(
        select(SectionSchedule.section_id, SectionSchedule.weekday, SectionSchedule.period).where(
            SectionSchedule.semester_id == semester_id
        )
    ):
        slots[section_id].add((weekday, period))
    return slots
