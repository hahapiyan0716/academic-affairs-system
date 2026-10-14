"""教師 API：開課、修改班級、查看名單、登錄成績"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.middleware.require_auth import TeacherUser, teacher_id_of
from app.routes.error_responses import errors
from app.schemas.section_schema import GradesResult, GradesUpdate, RosterOut, SectionCreate, SectionOut, SectionUpdate
from app.schemas.teacher_schema import TeacherMeOut
from app.services import section_service, teacher_service

# 每支 API 都限定教師身分：未登入 401、角色不符或帳號未連結教師資料 403
router = APIRouter(prefix="/api/teacher", tags=["teacher"], responses=errors(401, 403))

DB = Annotated[Session, Depends(get_db)]

# 教師代碼一律取自登入身分（teacher_id_of）；service 再檢查班級是否屬於該教師


@router.get("/me", response_model=TeacherMeOut, status_code=status.HTTP_200_OK, responses=errors(404))
def me(user: TeacherUser, db: DB):
    """教師本人資料；開課權限即時查資料庫"""
    return teacher_service.get_teacher(db, teacher_id_of(user))


@router.get("/sections", response_model=list[SectionOut], status_code=status.HTTP_200_OK)
def my_sections(user: TeacherUser, db: DB, semester_id: str | None = None):
    """自己授課（含合授）的班級，不指定學期則列出歷年全部"""
    return section_service.list_my_sections(db, teacher_id_of(user), semester_id)


# 403：沒有開課權限；404：學期、課程、教室或合授教師不存在；409：非開課期間、教師衝堂、教室衝突、班別重複
@router.post(
    "/sections", response_model=SectionOut, status_code=status.HTTP_201_CREATED, responses=errors(404, 409)
)
def create_section(user: TeacherUser, db: DB, body: SectionCreate):
    """開課；需具備開課權限，且學期須為規劃中或選課中"""
    section = section_service.create_section(db, teacher_id_of(user), body)
    # 回傳 View 的明細（含教師姓名、時段文字、人數），與列表格式一致
    return section_service.get_detail(db, section.section_id)


# 404：不是自己授課的班；409：非開課期間、上限低於已選人數、仍有學生選修不可停開
@router.patch(
    "/sections/{section_id}", response_model=SectionOut, status_code=status.HTTP_200_OK, responses=errors(404, 409)
)
def update_section(user: TeacherUser, db: DB, section_id: int, body: SectionUpdate):
    """修改人數上限，或停開班級"""
    section_service.update_section(db, teacher_id_of(user), section_id, body)
    return section_service.get_detail(db, section_id)


@router.get(
    "/sections/{section_id}/roster", response_model=RosterOut, status_code=status.HTTP_200_OK, responses=errors(404)
)
def roster(user: TeacherUser, db: DB, section_id: int):
    """修課名單與目前成績"""
    return section_service.get_roster(db, teacher_id_of(user), section_id)


# 404：不是自己授課的班，或名單中沒有這些學生；409：學期不是上課中或已結束
@router.put(
    "/sections/{section_id}/grades", response_model=GradesResult, status_code=status.HTTP_200_OK, responses=errors(404, 409)
)
def update_grades(user: TeacherUser, db: DB, section_id: int, body: GradesUpdate):
    """批次登錄成績；user_id 寫入稽核紀錄的操作者欄位"""
    return section_service.update_grades(db, teacher_id_of(user), user.user_id, section_id, body)
