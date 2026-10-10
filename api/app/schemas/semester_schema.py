"""學期與管理員統計"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel


class SemesterOut(ORMModel):
    """學期"""

    semester_id: str
    acad_year: int
    term: int
    status: str
    is_current: bool


class SemesterCreateIn(BaseModel):
    """管理員新增學期；學期代碼由學年與學期組成，不由前端傳入"""

    acad_year: int = Field(ge=100, le=999)  # 民國學年（三位數）
    term: int = Field(ge=1, le=3)  # 第幾學期（與資料庫的 chk_semester_term 一致）


class SemesterUpdateIn(BaseModel):
    """管理員修改學期狀態或設為目前學期；只更新有傳入的欄位"""

    status: Literal["Planning", "Enrolling", "InProgress", "Finished"] | None = None
    # 只能「設為目前學期」；其他學期的旗標會在同一個交易內清除
    is_current: Literal[True] | None = None


class AdminSemesterOut(SemesterOut):
    """管理員的學期列表：多了該學期的開班數"""

    section_count: int


class StatsOut(BaseModel):
    """管理員首頁的統計數字"""

    users: int
    teachers_with_permission: int
    enrolled_students: int
    active_courses: int
    current_semester: AdminSemesterOut | None
