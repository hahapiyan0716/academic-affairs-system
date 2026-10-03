"""所有已登入角色皆可使用的查詢 API"""

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    ACTIVE_ENROLLMENT,
    Building,
    Course,
    Enrollment,
    Room,
    SectionDetailView,
    SectionSchedule,
    Semester,
    Teacher,
)
from app.schemas import BrowseSectionOut, CourseOut, RoomOut, SectionOut, SemesterOut
from app.security import AnyUser

router = APIRouter(prefix="/api", tags=["common"])

DB = Annotated[Session, Depends(get_db)]


def resolve_semester(db: Session, semester_id: str | None) -> Semester:
    """未指定學期時使用「目前學期」"""
    stmt = select(Semester).where(
        Semester.semester_id == semester_id if semester_id else Semester.is_current.is_(True)
    )
    semester = db.scalar(stmt)
    if semester is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到學期（或尚未設定目前學期）")
    return semester


@router.get("/semesters", response_model=list[SemesterOut])
def list_semesters(_: AnyUser, db: DB):
    return db.scalars(select(Semester).order_by(Semester.semester_id.desc())).all()


@router.get("/rooms", response_model=list[RoomOut])
def list_rooms(_: AnyUser, db: DB):
    rows = db.execute(
        select(Room.room_code, Building.building_name, Room.seat_capacity)
        .join(Building, Building.building_id == Room.building_id)
        .order_by(Building.building_name, Room.room_code)
    ).all()
    return [RoomOut(room_code=r, building_name=b, seat_capacity=c) for r, b, c in rows]


@router.get("/courses", response_model=list[CourseOut])
def list_courses(_: AnyUser, db: DB):
    return db.scalars(select(Course).where(Course.is_active.is_(True)).order_by(Course.course_no)).all()


@router.get("/teachers")
def list_teachers(_: AnyUser, db: DB):
    rows = db.execute(select(Teacher.teacher_id, Teacher.teacher_name).order_by(Teacher.teacher_id)).all()
    return [{"teacher_id": t, "teacher_name": n} for t, n in rows]


@router.get("/sections", response_model=list[BrowseSectionOut])
def browse_sections(
    user: AnyUser,
    db: DB,
    semester_id: str | None = None,
    q: Annotated[str | None, Query(max_length=30)] = None,
):
    """瀏覽某學期（預設目前學期）的開放班級；學生會額外得到自己的選課狀態與衝堂標記"""
    semester = resolve_semester(db, semester_id)
    stmt = select(SectionDetailView).where(
        SectionDetailView.semester_id == semester.semester_id,
        SectionDetailView.status == "Open",
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                SectionDetailView.course_name.like(like),
                SectionDetailView.course_no.like(like),
                SectionDetailView.teacher_names.like(like),
            )
        )
    sections = db.scalars(stmt.order_by(SectionDetailView.course_no, SectionDetailView.section_code)).all()
    result = [BrowseSectionOut.model_validate(s, from_attributes=True) for s in sections]

    if user.role == "Student" and user.student_id and result:
        my_status = dict(
            db.execute(
                select(Enrollment.section_id, Enrollment.status).where(
                    Enrollment.student_id == user.student_id,
                    Enrollment.section_id.in_([s.section_id for s in result]),
                )
            ).all()
        )
        # 學生已選上課程佔用的時段
        busy = set(
            db.execute(
                select(SectionSchedule.weekday, SectionSchedule.period)
                .join(Enrollment, Enrollment.section_id == SectionSchedule.section_id)
                .where(
                    Enrollment.student_id == user.student_id,
                    Enrollment.status.in_(ACTIVE_ENROLLMENT),
                    SectionSchedule.semester_id == semester.semester_id,
                )
            ).all()
        )
        slots: dict[int, set[tuple[int, int]]] = defaultdict(set)
        for sid, w, p in db.execute(
            select(SectionSchedule.section_id, SectionSchedule.weekday, SectionSchedule.period).where(
                SectionSchedule.semester_id == semester.semester_id
            )
        ):
            slots[sid].add((w, p))

        for s in result:
            status_ = my_status.get(s.section_id)
            s.my_status = str(status_) if status_ else None
            is_mine = status_ in ACTIVE_ENROLLMENT
            s.conflict = not is_mine and bool(slots[s.section_id] & busy)
    return result


@router.get("/history/sections")
def history_sections(
    _: AnyUser,
    db: DB,
    course_no: str | None = None,
    teacher: Annotated[str | None, Query(max_length=30)] = None,
    q: Annotated[str | None, Query(max_length=30)] = None,
):
    """
    歷年開課紀錄：跨學期查詢某課程由哪些教師開設、修課人數與平均成績。

    平均成績以子查詢計算，對應 SQL：
      SELECT v.*, (SELECT ROUND(AVG(e.score), 1) FROM Enrollment e
                    WHERE e.section_id = v.section_id AND e.status IN ('Selected','Manual')) AS avg_score
        FROM v_section_detail v ...
    """
    avg_score = (
        select(func.round(func.avg(Enrollment.score), 1))
        .where(
            Enrollment.section_id == SectionDetailView.section_id,
            Enrollment.status.in_(ACTIVE_ENROLLMENT),
        )
        .correlate(SectionDetailView)
        .scalar_subquery()
    )
    stmt = select(SectionDetailView, avg_score.label("avg_score"))
    if course_no:
        stmt = stmt.where(SectionDetailView.course_no == course_no)
    if teacher:
        stmt = stmt.where(SectionDetailView.teacher_names.like(f"%{teacher}%"))
    if q:
        stmt = stmt.where(
            or_(SectionDetailView.course_name.like(f"%{q}%"), SectionDetailView.course_no.like(f"%{q}%"))
        )
    rows = db.execute(
        stmt.order_by(SectionDetailView.semester_id.desc(), SectionDetailView.course_no).limit(500)
    ).all()
    return [
        {**SectionOut.model_validate(view, from_attributes=True).model_dump(), "avg_score": avg}
        for view, avg in rows
    ]
