"""教師 API：開課、修改班級、查看名單、登錄成績"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.middleware.require_auth import TeacherUser, teacher_id_of
from app.schemas.section_schema import GradesResult, GradesUpdate, RosterOut, SectionCreate, SectionOut, SectionUpdate
from app.schemas.teacher_schema import TeacherMeOut
from app.services import section_service, teacher_service

router = APIRouter(prefix="/api/teacher", tags=["teacher"])

DB = Annotated[Session, Depends(get_db)]


@router.get("/me", response_model=TeacherMeOut)
def me(user: TeacherUser, db: DB):
    return teacher_service.get_teacher(db, teacher_id_of(user))


@router.get("/sections", response_model=list[SectionOut])
def my_sections(user: TeacherUser, db: DB, semester_id: str | None = None):
    """自己授課（含合授）的班級，不指定學期則列出歷年全部"""
    return section_service.list_my_sections(db, teacher_id_of(user), semester_id)


@router.post("/sections", response_model=SectionOut, status_code=status.HTTP_201_CREATED)
def create_section(user: TeacherUser, db: DB, body: SectionCreate):
    section = section_service.create_section(db, teacher_id_of(user), body)
    return section_service.get_detail(db, section.section_id)


@router.patch("/sections/{section_id}", response_model=SectionOut)
def update_section(user: TeacherUser, db: DB, section_id: int, body: SectionUpdate):
    section_service.update_section(db, teacher_id_of(user), section_id, body)
    return section_service.get_detail(db, section_id)


@router.get("/sections/{section_id}/roster", response_model=RosterOut)
def roster(user: TeacherUser, db: DB, section_id: int):
    return section_service.get_roster(db, teacher_id_of(user), section_id)


@router.put("/sections/{section_id}/grades", response_model=GradesResult)
def update_grades(user: TeacherUser, db: DB, section_id: int, body: GradesUpdate):
    return section_service.update_grades(db, teacher_id_of(user), user.user_id, section_id, body)
