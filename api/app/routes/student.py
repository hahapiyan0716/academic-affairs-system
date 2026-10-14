"""學生 API：加退選、本學期課表、歷年成績"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.middleware.require_auth import StudentUser, student_id_of
from app.routes.error_responses import errors
from app.schemas.enrollment_schema import EnrollIn, EnrollmentOut, TimetableOut, TranscriptOut
from app.services import enrollment_service

# 每支 API 都限定學生身分：未登入 401、角色不符或帳號未連結學生資料 403
router = APIRouter(prefix="/api", tags=["student"], responses=errors(401, 403))

DB = Annotated[Session, Depends(get_db)]

# 學號一律取自登入身分（student_id_of），學生無法替他人加退選


# 403：非在學狀態；404：班級不存在；409：額滿、衝堂、重複修課、已停開或非選課期間
@router.post(
    "/enrollments", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED, responses=errors(404, 409)
)
def enroll(user: StudentUser, db: DB, body: EnrollIn):
    """加選（先搶先贏）"""
    return enrollment_service.enroll(db, student_id_of(user), body.section_id)


# 回傳 200 而非 204：退選後仍回傳這筆選課紀錄；404：未選修此班級；409：非選課期間或已有成績
@router.delete(
    "/enrollments/{section_id}", response_model=EnrollmentOut, status_code=status.HTTP_200_OK, responses=errors(404, 409)
)
def withdraw(user: StudentUser, db: DB, section_id: int):
    """退選：紀錄不刪除，狀態改為 Withdrawn，前端會顯示為「已退選」；只有學期為選課中、且尚未有成績時才能退選"""
    return enrollment_service.withdraw(db, student_id_of(user), section_id)


# 404：指定的學期不存在，或尚未設定目前學期
@router.get("/me/timetable", response_model=TimetableOut, status_code=status.HTTP_200_OK, responses=errors(404))
def timetable(user: StudentUser, db: DB, semester_id: str | None = None):
    """課表：已選上的班級清單 + 攤平的時段格（前端據此畫週課表）"""
    return enrollment_service.timetable(db, student_id_of(user), semester_id)


@router.get("/me/transcript", response_model=TranscriptOut, status_code=status.HTTP_200_OK)
def transcript(user: StudentUser, db: DB):
    """歷年成績：按學期分組，含學分與學分加權平均"""
    return enrollment_service.transcript(db, student_id_of(user))
