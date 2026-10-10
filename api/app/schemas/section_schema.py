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
    field_names: str | None  # 課程領域，以「、」串接


class BrowseSectionOut(SectionOut):
    """瀏覽班級的結果；兩個額外欄位只有學生查詢時才會填入"""

    my_status: str | None = None  # 目前學生對此班的選課狀態
    conflict: bool = False  # 是否與學生已選課程衝堂


class HistorySectionOut(SectionOut):
    """歷年開課查詢的結果"""

    avg_score: Decimal | None  # 有效選課者的平均成績（四捨五入到小數 1 位）


# ---------------------------------------------------------------------
# 教師：開課
# ---------------------------------------------------------------------


class TimeSlotIn(BaseModel):
    """開課時的一個上課時段：星期（1–7）、節次（1–14）與教室"""

    weekday: int = Field(ge=1, le=7)
    period: int = Field(ge=1, le=14)
    room_code: str = Field(min_length=1, max_length=10)


class SectionCreate(BaseModel):
    """教師開課；開課者本人自動成為主授教師，不必列在 co_teacher_ids"""

    course_no: str = Field(min_length=5, max_length=5)
    semester_id: str = Field(min_length=4, max_length=4)
    # 允許只輸入 "1"，service 會補零成 "01"
    section_code: str = Field(default="01", min_length=1, max_length=2)
    capacity: int = Field(ge=1, le=500)
    co_teacher_ids: list[str] = Field(default_factory=list, max_length=5)  # 合授教師
    slots: list[TimeSlotIn] = Field(min_length=1, max_length=20)

    @field_validator("slots")
    @classmethod
    def unique_slots(cls, v: list[TimeSlotIn]) -> list[TimeSlotIn]:
        """同一個（星期, 節次）只能出現一次，即使教室不同"""
        keys = {(s.weekday, s.period) for s in v}
        if len(keys) != len(v):
            raise ValueError("同一個班級的上課時段不可重複")
        return v


class SectionUpdate(BaseModel):
    """教師修改班級設定；只更新有傳入的欄位"""

    capacity: int | None = Field(default=None, ge=1, le=500)
    # 只允許「停開」；停開後時段即釋放，不提供恢復
    status: str | None = Field(default=None, pattern="^Cancelled$")


# ---------------------------------------------------------------------
# 教師：名單與成績
# ---------------------------------------------------------------------


class RosterEntry(BaseModel):
    """修課名單的一列"""

    student_id: str
    student_name: str
    dept_name: str
    degree: int  # 0 = 大學部、1 = 碩博班（及格標準不同）
    status: str
    score: Decimal | None
    feedback_rank: int | None


class RosterOut(BaseModel):
    """班級修課名單"""

    section: SectionOut
    semester_status: str
    gradable: bool  # 學期狀態是否允許登分，前端據此決定成績欄可否編輯
    students: list[RosterEntry]


class GradeIn(BaseModel):
    """一位學生的成績；score 為 None 表示清除成績"""

    student_id: str
    score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=4, decimal_places=1)


class GradesUpdate(BaseModel):
    """批次登分的請求內容"""

    grades: list[GradeIn] = Field(min_length=1, max_length=500)


class GradesResult(BaseModel):
    """批次登分的結果：實際變更與成績未變的筆數"""

    updated: int
    unchanged: int
