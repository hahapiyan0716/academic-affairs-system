"""學生 API：加退選、本學期課表、歷年成績"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    ACTIVE_ENROLLMENT,
    Course,
    Enrollment,
    Section,
    SectionDetailView,
    SectionSchedule,
    TranscriptView,
)
from app.routers.common import resolve_semester
from app.schemas import (
    EnrollIn,
    EnrollmentOut,
    SectionOut,
    TimetableOut,
    TimetableSlot,
    TranscriptOut,
    TranscriptRow,
    TranscriptSemester,
)
from app.security import CurrentUser, StudentUser
from app.services import enrollment as svc

router = APIRouter(prefix="/api", tags=["student"])

DB = Annotated[Session, Depends(get_db)]


def _student_id(user: CurrentUser) -> str:
    if not user.student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "此帳號未連結學生資料")
    return user.student_id


@router.post("/enrollments", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enroll(user: StudentUser, db: DB, body: EnrollIn):
    e = svc.enroll(db, _student_id(user), body.section_id)
    return EnrollmentOut(student_id=e.student_id, section_id=e.section_id, status=e.status)


@router.delete("/enrollments/{section_id}", response_model=EnrollmentOut)
def withdraw(user: StudentUser, db: DB, section_id: int):
    e = svc.withdraw(db, _student_id(user), section_id)
    return EnrollmentOut(student_id=e.student_id, section_id=e.section_id, status=e.status)


@router.get("/me/timetable", response_model=TimetableOut)
def timetable(user: StudentUser, db: DB, semester_id: str | None = None):
    """課表：已選上的班級清單 + 攤平的時段格（前端據此畫週課表）"""
    student_id = _student_id(user)
    semester = resolve_semester(db, semester_id)

    my_sections = (
        select(Enrollment.section_id)
        .join(Section, Section.section_id == Enrollment.section_id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status.in_(ACTIVE_ENROLLMENT),
            Section.semester_id == semester.semester_id,
        )
    )
    sections = db.scalars(
        select(SectionDetailView)
        .where(SectionDetailView.section_id.in_(my_sections))
        .order_by(SectionDetailView.course_no)
    ).all()
    slots = db.execute(
        select(
            SectionSchedule.weekday,
            SectionSchedule.period,
            SectionSchedule.room_code,
            Section.section_id,
            Course.course_no,
            Course.course_name,
        )
        .join(Section, Section.section_id == SectionSchedule.section_id)
        .join(Course, Course.course_no == Section.course_no)
        .where(SectionSchedule.section_id.in_(my_sections))
        .order_by(SectionSchedule.weekday, SectionSchedule.period)
    ).all()

    return TimetableOut(
        semester_id=semester.semester_id,
        total_credits=sum(s.credit for s in sections),
        sections=[SectionOut.model_validate(s) for s in sections],
        slots=[TimetableSlot(**row._mapping) for row in slots],
    )


def _weighted_avg(rows: list[TranscriptRow]) -> Decimal | None:
    """學分加權平均：Σ(成績 × 學分) / Σ(學分)，只計入已有成績的課程"""
    graded = [r for r in rows if r.score is not None]
    credits = sum(r.credit for r in graded)
    if credits == 0:
        return None
    total = sum((r.score or Decimal(0)) * r.credit for r in graded)
    return (total / credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("/me/transcript", response_model=TranscriptOut)
def transcript(user: StudentUser, db: DB):
    """歷年成績：資料來自 v_student_transcript，按學期分組並計算學分與加權平均"""
    rows = [
        TranscriptRow.model_validate(r)
        for r in db.scalars(
            select(TranscriptView)
            .where(TranscriptView.student_id == _student_id(user))
            .order_by(TranscriptView.semester_id.desc(), TranscriptView.course_no)
        )
    ]
    grouped: dict[str, list[TranscriptRow]] = defaultdict(list)
    for r in rows:
        grouped[r.semester_id].append(r)

    semesters = [
        TranscriptSemester(
            semester_id=sem,
            rows=items,
            credits_taken=sum(r.credit for r in items),
            credits_earned=sum(r.credit for r in items if r.passed == 1),
            average=_weighted_avg(items),
        )
        for sem, items in grouped.items()
    ]
    return TranscriptOut(
        semesters=semesters,
        total_credits_earned=sum(s.credits_earned for s in semesters),
        overall_average=_weighted_avg(rows),
    )
