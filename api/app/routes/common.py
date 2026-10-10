"""所有已登入角色皆可使用的查詢 API"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.middleware.require_auth import AnyUser
from app.schemas.common_schema import RoomOut
from app.schemas.course_schema import CourseOut
from app.schemas.section_schema import BrowseSectionOut, HistorySectionOut
from app.schemas.semester_schema import SemesterOut
from app.schemas.teacher_schema import TeacherBriefOut
from app.services import course_service, section_service, semester_service, teacher_service

router = APIRouter(prefix="/api", tags=["common"])

DB = Annotated[Session, Depends(get_db)]
Keyword = Annotated[str | None, Query(max_length=30)]
FieldName = Annotated[str | None, Query(max_length=50)]  # 與 CurriculumField.field_name 長度一致


@router.get("/semesters", response_model=list[SemesterOut])
def list_semesters(_: AnyUser, db: DB):
    return semester_service.list_semesters(db)


@router.get("/rooms", response_model=list[RoomOut])
def list_rooms(_: AnyUser, db: DB):
    return section_service.list_rooms(db)


@router.get("/courses", response_model=list[CourseOut])
def list_courses(_: AnyUser, db: DB):
    return course_service.list_active(db)


@router.get("/fields", response_model=list[str])
def list_fields(_: AnyUser, db: DB):
    """課程領域清單（篩選用下拉選單）"""
    return course_service.list_field_names(db)


@router.get("/teachers", response_model=list[TeacherBriefOut])
def list_teachers(_: AnyUser, db: DB):
    return teacher_service.list_brief(db)


@router.get("/sections", response_model=list[BrowseSectionOut])
def browse_sections(
    user: AnyUser, db: DB, semester_id: str | None = None, q: Keyword = None, field: FieldName = None
):
    """瀏覽某學期（預設目前學期）的開放班級；學生會額外得到自己的選課狀態與衝堂標記"""
    return section_service.browse(db, user, semester_id, q, field)


@router.get("/history/sections", response_model=list[HistorySectionOut])
def history_sections(
    _: AnyUser,
    db: DB,
    course_no: str | None = None,
    teacher: Keyword = None,
    q: Keyword = None,
    field: FieldName = None,
):
    """歷年開課紀錄：跨學期查詢某課程由哪些教師開設、修課人數與平均成績"""
    return section_service.history(db, course_no, teacher, q, field)
