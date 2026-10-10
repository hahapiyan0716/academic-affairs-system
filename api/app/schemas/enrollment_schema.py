"""學生：選課、課表、成績單"""

from decimal import Decimal

from pydantic import BaseModel

from app.schemas.base import ORMModel
from app.schemas.section_schema import SectionOut


class EnrollIn(BaseModel):
    """加選的請求內容；學號取自登入身分，不由前端傳入"""

    section_id: int


class EnrollmentOut(ORMModel):
    """加選／退選後的選課紀錄"""

    student_id: str
    section_id: int
    status: str


class TimetableSlot(BaseModel):
    """課表中的一格：某星期某節在某教室上某門課"""

    weekday: int
    period: int
    room_code: str
    section_id: int
    course_no: str
    course_name: str


class TimetableOut(BaseModel):
    """學生某學期的課表"""

    semester_id: str
    total_credits: int  # 本學期已選學分數
    sections: list[SectionOut]  # 已選上的班級清單
    slots: list[TimetableSlot]  # 攤平的時段格，前端據此畫週課表


class TranscriptRow(ORMModel):
    """成績單的一列，對應 v_student_transcript"""

    semester_id: str
    section_id: int
    course_no: str
    course_name: str
    course_type: str
    credit: int
    status: str
    score: Decimal | None
    passed: int | None  # 1 = 及格、0 = 不及格、None = 尚未登分
    field_names: str | None  # 課程領域，以「、」串接


class TranscriptSemester(BaseModel):
    """成績單中的一個學期"""

    semester_id: str
    rows: list[TranscriptRow]
    credits_taken: int  # 修習學分（不論是否及格）
    credits_earned: int  # 實得學分（只計及格的課程）
    average: Decimal | None  # 學分加權平均；整學期都還沒有成績時為 None


class TranscriptOut(BaseModel):
    """學生歷年成績單"""

    semesters: list[TranscriptSemester]
    total_credits_earned: int
    overall_average: Decimal | None  # 歷年學分加權平均
