"""開課班級、修課名單、登分"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import ORMModel


class SectionOut(ORMModel):
    """對應 v_section_detail"""

    section_id: int
    semester_id: str
    course_no: str
    course_name: str
    course_type: str
    credit: int
    section_code: str
    capacity: int
    status: str
    teacher_names: str | None
    schedule_text: str | None
    enrolled_count: int


class BrowseSectionOut(SectionOut):
    my_status: str | None = None  # 目前學生對此班的選課狀態
    conflict: bool = False  # 是否與學生已選課程衝堂


class HistorySectionOut(SectionOut):
    avg_score: Decimal | None  # 有效選課者的平均成績（四捨五入到小數 1 位）


# ---------------------------------------------------------------------
# 教師：開課
# ---------------------------------------------------------------------


class TimeSlotIn(BaseModel):
    weekday: int = Field(ge=1, le=7)
    period: int = Field(ge=1, le=14)
    room_code: str = Field(min_length=1, max_length=10)


class SectionCreate(BaseModel):
    course_no: str = Field(min_length=5, max_length=5)
    semester_id: str = Field(min_length=4, max_length=4)
    section_code: str = Field(default="01", min_length=1, max_length=2)
    capacity: int = Field(ge=1, le=500)
    co_teacher_ids: list[str] = Field(default_factory=list, max_length=5)
    slots: list[TimeSlotIn] = Field(min_length=1, max_length=20)

    @field_validator("slots")
    @classmethod
    def unique_slots(cls, v: list[TimeSlotIn]) -> list[TimeSlotIn]:
        keys = {(s.weekday, s.period) for s in v}
        if len(keys) != len(v):
            raise ValueError("同一個班級的上課時段不可重複")
        return v


class SectionUpdate(BaseModel):
    capacity: int | None = Field(default=None, ge=1, le=500)
    # 只允許「停開」；停開後時段即釋放，不提供恢復
    status: str | None = Field(default=None, pattern="^Cancelled$")


# ---------------------------------------------------------------------
# 教師：名單與成績
# ---------------------------------------------------------------------


class RosterEntry(BaseModel):
    student_id: str
    student_name: str
    dept_name: str
    degree: int
    status: str
    score: Decimal | None
    feedback_rank: int | None


class RosterOut(BaseModel):
    section: SectionOut
    semester_status: str
    gradable: bool
    students: list[RosterEntry]


class GradeIn(BaseModel):
    student_id: str
    score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=4, decimal_places=1)


class GradesUpdate(BaseModel):
    grades: list[GradeIn] = Field(min_length=1, max_length=500)


class GradesResult(BaseModel):
    updated: int
    unchanged: int
