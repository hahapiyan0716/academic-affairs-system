"""教師 API：開課、修改班級、查看名單、登錄成績"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    ACTIVE_ENROLLMENT,
    Course,
    Department,
    Enrollment,
    SectionDetailView,
    Semester,
    SectionTeacher,
    Student,
    Teacher,
)
from app.schemas import (
    GradesResult,
    GradesUpdate,
    RosterEntry,
    SectionCreate,
    SectionOut,
    SectionUpdate,
)
from app.security import CurrentUser, TeacherUser
from app.services import sections as svc

router = APIRouter(prefix="/api/teacher", tags=["teacher"])

DB = Annotated[Session, Depends(get_db)]


def _teacher_id(user: CurrentUser) -> str:
    if not user.teacher_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "此帳號未連結教師資料")
    return user.teacher_id


def _detail(db: Session, section_id: int) -> SectionDetailView:
    view = db.get(SectionDetailView, section_id)
    assert view is not None
    return view


@router.get("/me")
def me(user: TeacherUser, db: DB):
    """教師基本資料；can_open_section 以資料庫為準，前端據此決定是否顯示「新增開課」"""
    teacher = db.get(Teacher, _teacher_id(user))
    if teacher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到教師資料")
    return {
        "teacher_id": teacher.teacher_id,
        "teacher_name": teacher.teacher_name,
        "can_open_section": teacher.can_open_section,
    }


@router.get("/sections", response_model=list[SectionOut])
def my_sections(user: TeacherUser, db: DB, semester_id: str | None = None):
    """自己授課（含合授）的班級，不指定學期則列出歷年全部"""
    stmt = (
        select(SectionDetailView)
        .join(SectionTeacher, SectionTeacher.section_id == SectionDetailView.section_id)
        .where(SectionTeacher.teacher_id == _teacher_id(user))
    )
    if semester_id:
        stmt = stmt.where(SectionDetailView.semester_id == semester_id)
    return db.scalars(stmt.order_by(SectionDetailView.semester_id.desc(), SectionDetailView.course_no)).all()


@router.post("/sections", response_model=SectionOut, status_code=status.HTTP_201_CREATED)
def create_section(user: TeacherUser, db: DB, body: SectionCreate):
    section = svc.create_section(db, _teacher_id(user), body)
    return _detail(db, section.section_id)


@router.patch("/sections/{section_id}", response_model=SectionOut)
def update_section(user: TeacherUser, db: DB, section_id: int, body: SectionUpdate):
    svc.update_section(db, _teacher_id(user), section_id, body)
    return _detail(db, section_id)


@router.get("/sections/{section_id}/roster")
def roster(user: TeacherUser, db: DB, section_id: int):
    """修課名單（只列中選／人工加選者），附系所與目前成績"""
    section = svc.get_owned_section(db, _teacher_id(user), section_id)
    rows = db.execute(
        select(
            Student.student_id,
            Student.student_name,
            Department.dept_name,
            Student.degree,
            Enrollment.status,
            Enrollment.score,
            Enrollment.feedback_rank,
        )
        .select_from(Enrollment)
        .join(Student, Student.student_id == Enrollment.student_id)
        .join(Department, Department.dept_id == Student.dept_id)
        .where(Enrollment.section_id == section_id, Enrollment.status.in_(ACTIVE_ENROLLMENT))
        .order_by(Student.student_id)
    ).all()
    semester = db.get(Semester, section.semester_id)
    course = db.get(Course, section.course_no)
    assert semester is not None and course is not None
    return {
        "section": SectionOut.model_validate(_detail(db, section_id), from_attributes=True),
        "semester_status": semester.status,
        "gradable": semester.status in svc.GRADABLE,
        "students": [
            RosterEntry(
                student_id=sid, student_name=name, dept_name=dept, degree=deg,
                status=st, score=score, feedback_rank=fb,
            )
            for sid, name, dept, deg, st, score, fb in rows
        ],
    }


@router.put("/sections/{section_id}/grades", response_model=GradesResult)
def update_grades(user: TeacherUser, db: DB, section_id: int, body: GradesUpdate):
    return svc.update_grades(db, _teacher_id(user), user.user_id, section_id, body)
