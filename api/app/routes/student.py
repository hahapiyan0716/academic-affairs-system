"""學生 API：加退選、本學期課表、歷年成績"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.middleware.require_auth import StudentUser, student_id_of
from app.schemas.enrollment_schema import EnrollIn, EnrollmentOut, TimetableOut, TranscriptOut
from app.services import enrollment_service

router = APIRouter(prefix="/api", tags=["student"])

DB = Annotated[Session, Depends(get_db)]


@router.post("/enrollments", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enroll(user: StudentUser, db: DB, body: EnrollIn):
    return enrollment_service.enroll(db, student_id_of(user), body.section_id)


@router.delete("/enrollments/{section_id}", response_model=EnrollmentOut)
def withdraw(user: StudentUser, db: DB, section_id: int):
    return enrollment_service.withdraw(db, student_id_of(user), section_id)


@router.get("/me/timetable", response_model=TimetableOut)
def timetable(user: StudentUser, db: DB, semester_id: str | None = None):
    """課表：已選上的班級清單 + 攤平的時段格（前端據此畫週課表）"""
    return enrollment_service.timetable(db, student_id_of(user), semester_id)


@router.get("/me/transcript", response_model=TranscriptOut)
def transcript(user: StudentUser, db: DB):
    """歷年成績：按學期分組，含學分與學分加權平均"""
    return enrollment_service.transcript(db, student_id_of(user))
