"""學生：選課、課表、成績單"""

from decimal import Decimal

from pydantic import BaseModel

from app.schemas.base import ORMModel
from app.schemas.section_schema import SectionOut


class EnrollIn(BaseModel):
    section_id: int


class EnrollmentOut(ORMModel):
    student_id: str
    section_id: int
    status: str


class TimetableSlot(BaseModel):
    weekday: int
    period: int
    room_code: str
    section_id: int
    course_no: str
    course_name: str


class TimetableOut(BaseModel):
    semester_id: str
    total_credits: int
    sections: list[SectionOut]
    slots: list[TimetableSlot]


class TranscriptRow(ORMModel):
    semester_id: str
    section_id: int
    course_no: str
    course_name: str
    course_type: str
    credit: int
    status: str
    score: Decimal | None
    passed: int | None


class TranscriptSemester(BaseModel):
    semester_id: str
    rows: list[TranscriptRow]
    credits_taken: int
    credits_earned: int
    average: Decimal | None  # 學分加權平均


class TranscriptOut(BaseModel):
    semesters: list[TranscriptSemester]
    total_credits_earned: int
    overall_average: Decimal | None
