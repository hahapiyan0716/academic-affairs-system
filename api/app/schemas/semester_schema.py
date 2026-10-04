"""學期與管理員統計"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel


class SemesterOut(ORMModel):
    semester_id: str
    acad_year: int
    term: int
    status: str
    is_current: bool


class SemesterCreateIn(BaseModel):
    acad_year: int = Field(ge=100, le=999)
    term: int = Field(ge=1, le=3)


class SemesterUpdateIn(BaseModel):
    status: Literal["Planning", "Enrolling", "InProgress", "Finished"] | None = None
    # 只能「設為目前學期」；其他學期的旗標會在同一個交易內清除
    is_current: Literal[True] | None = None


class AdminSemesterOut(SemesterOut):
    section_count: int


class StatsOut(BaseModel):
    users: int
    teachers_with_permission: int
    enrolled_students: int
    active_courses: int
    current_semester: AdminSemesterOut | None
