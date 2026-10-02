"""
SQLAlchemy 2.0 ORM 模型。

Schema 的主控權在 Prisma（services/auth-admin/prisma/schema.prisma），
本檔只是「對應」既有資料表，絕不呼叫 Base.metadata.create_all()。
Prisma schema 變更後，必須手動同步本檔的欄位定義。
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CHAR,
    DECIMAL,
    VARCHAR,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    SmallInteger,
    func,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------
# 列舉（值須與 Prisma enum 完全相同）
# ---------------------------------------------------------------------


class StudentStatus(StrEnum):
    Enrolled = "Enrolled"
    Suspended = "Suspended"
    Dropped = "Dropped"


class CourseType(StrEnum):
    Required = "Required"
    Elective = "Elective"


class SemesterStatus(StrEnum):
    Planning = "Planning"
    Enrolling = "Enrolling"
    InProgress = "InProgress"
    Finished = "Finished"


class SectionStatus(StrEnum):
    Open = "Open"
    Cancelled = "Cancelled"


class EnrollmentStatus(StrEnum):
    Registered = "Registered"
    Selected = "Selected"
    Manual = "Manual"
    NotSelected = "NotSelected"
    Withdrawn = "Withdrawn"


# 「實際佔用名額／實際修課」的狀態
ACTIVE_ENROLLMENT = (EnrollmentStatus.Selected, EnrollmentStatus.Manual)


def _enum(cls: type[StrEnum]) -> Enum:
    # native_enum=True 對應 MySQL 的 ENUM 型別；validate_strings 讓錯誤值在 Python 端就被擋下
    return Enum(cls, native_enum=True, validate_strings=True, values_callable=lambda e: [m.value for m in e])


# ---------------------------------------------------------------------
# 人員
# ---------------------------------------------------------------------


class Department(Base):
    __tablename__ = "Department"

    dept_id: Mapped[str] = mapped_column(CHAR(4), primary_key=True)
    dept_name: Mapped[str] = mapped_column(VARCHAR(50))


class Teacher(Base):
    __tablename__ = "Teacher"

    teacher_id: Mapped[str] = mapped_column(CHAR(6), primary_key=True)
    teacher_name: Mapped[str] = mapped_column(VARCHAR(50))
    dept_id: Mapped[str | None] = mapped_column(CHAR(4))
    can_open_section: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[int | None] = mapped_column(Integer)


class Student(Base):
    __tablename__ = "Student"

    student_id: Mapped[str] = mapped_column(CHAR(10), primary_key=True)
    student_name: Mapped[str] = mapped_column(VARCHAR(30))
    dept_id: Mapped[str] = mapped_column(CHAR(4))
    grade: Mapped[int] = mapped_column(TINYINT)
    status: Mapped[StudentStatus] = mapped_column(_enum(StudentStatus))
    class_code: Mapped[str] = mapped_column(CHAR(2))
    degree: Mapped[int] = mapped_column(TINYINT, default=0)
    user_id: Mapped[int | None] = mapped_column(Integer)


# ---------------------------------------------------------------------
# 空間與課程庫
# ---------------------------------------------------------------------


class Building(Base):
    __tablename__ = "Building"

    building_id: Mapped[str] = mapped_column(CHAR(4), primary_key=True)
    building_name: Mapped[str] = mapped_column(VARCHAR(50))


class Room(Base):
    __tablename__ = "Room"

    room_code: Mapped[str] = mapped_column(VARCHAR(10), primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("Building.building_id"))
    seat_capacity: Mapped[int | None] = mapped_column(SmallInteger)

    building: Mapped[Building] = relationship()


class Course(Base):
    __tablename__ = "Course"

    course_no: Mapped[str] = mapped_column(CHAR(5), primary_key=True)
    course_name: Mapped[str] = mapped_column(VARCHAR(50))
    course_type: Mapped[CourseType] = mapped_column(_enum(CourseType))
    credit: Mapped[int] = mapped_column(TINYINT)
    dept_id: Mapped[str | None] = mapped_column(CHAR(4))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------------------------------------------------------------
# 學期與開課班級
# ---------------------------------------------------------------------


class Semester(Base):
    __tablename__ = "Semester"

    semester_id: Mapped[str] = mapped_column(CHAR(4), primary_key=True)
    acad_year: Mapped[int] = mapped_column(SmallInteger)
    term: Mapped[int] = mapped_column(TINYINT)
    status: Mapped[SemesterStatus] = mapped_column(_enum(SemesterStatus))
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)


class Section(Base):
    __tablename__ = "Section"

    section_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_no: Mapped[str] = mapped_column(ForeignKey("Course.course_no"))
    semester_id: Mapped[str] = mapped_column(ForeignKey("Semester.semester_id"))
    section_code: Mapped[str] = mapped_column(CHAR(2), default="01")
    capacity: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[SectionStatus] = mapped_column(_enum(SectionStatus), default=SectionStatus.Open)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("Teacher.teacher_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    course: Mapped[Course] = relationship()
    semester: Mapped[Semester] = relationship()
    teachers: Mapped[list["SectionTeacher"]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )
    schedules: Mapped[list["SectionSchedule"]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        # SectionSchedule 以 (section_id, semester_id) 複合外鍵參照 Section，
        # SQLAlchemy 會依此自動 JOIN 兩個欄位，並在新增時同時帶入 semester_id
        order_by="(SectionSchedule.weekday, SectionSchedule.period)",
    )


class SectionTeacher(Base):
    __tablename__ = "SectionTeacher"

    section_id: Mapped[int] = mapped_column(ForeignKey("Section.section_id"), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("Teacher.teacher_id"), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)

    section: Mapped[Section] = relationship(back_populates="teachers")
    teacher: Mapped[Teacher] = relationship()


class SectionSchedule(Base):
    __tablename__ = "SectionSchedule"
    __table_args__ = (
        ForeignKeyConstraint(
            ["section_id", "semester_id"], ["Section.section_id", "Section.semester_id"]
        ),
    )

    schedule_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(Integer)
    semester_id: Mapped[str] = mapped_column(CHAR(4))
    room_code: Mapped[str] = mapped_column(ForeignKey("Room.room_code"))
    weekday: Mapped[int] = mapped_column(TINYINT)
    period: Mapped[int] = mapped_column(TINYINT)

    section: Mapped[Section] = relationship(back_populates="schedules")


# ---------------------------------------------------------------------
# 選課與成績
# ---------------------------------------------------------------------


class Enrollment(Base):
    __tablename__ = "Enrollment"

    student_id: Mapped[str] = mapped_column(ForeignKey("Student.student_id"), primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("Section.section_id"), primary_key=True)
    status: Mapped[EnrollmentStatus] = mapped_column(_enum(EnrollmentStatus))
    score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    feedback_rank: Mapped[int | None] = mapped_column(TINYINT)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Prisma 的 @updatedAt 只在 Prisma Client 端生效，SQLAlchemy 這邊需自行設定 onupdate
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    student: Mapped[Student] = relationship()
    section: Mapped[Section] = relationship()


class ScoreChangeLog(Base):
    __tablename__ = "ScoreChangeLog"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_id", "section_id"], ["Enrollment.student_id", "Enrollment.section_id"]
        ),
    )

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(CHAR(10))
    section_id: Mapped[int] = mapped_column(Integer)
    old_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    new_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    changed_by: Mapped[int] = mapped_column(Integer)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------
# View（唯讀）：定義於 Prisma migration 的手寫 SQL
# ---------------------------------------------------------------------


class SectionDetailView(Base):
    __tablename__ = "v_section_detail"
    __table_args__ = {"info": {"is_view": True}}

    section_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_id: Mapped[str] = mapped_column(CHAR(4))
    course_no: Mapped[str] = mapped_column(CHAR(5))
    course_name: Mapped[str] = mapped_column(VARCHAR(50))
    course_type: Mapped[str] = mapped_column(VARCHAR(10))
    credit: Mapped[int] = mapped_column(Integer)
    section_code: Mapped[str] = mapped_column(CHAR(2))
    capacity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(VARCHAR(10))
    created_by: Mapped[str | None] = mapped_column(CHAR(6))
    teacher_names: Mapped[str | None] = mapped_column(VARCHAR(500))
    schedule_text: Mapped[str | None] = mapped_column(VARCHAR(500))
    enrolled_count: Mapped[int] = mapped_column(Integer)


class TranscriptView(Base):
    __tablename__ = "v_student_transcript"
    __table_args__ = {"info": {"is_view": True}}

    student_id: Mapped[str] = mapped_column(CHAR(10), primary_key=True)
    section_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_id: Mapped[str] = mapped_column(CHAR(4))
    course_no: Mapped[str] = mapped_column(CHAR(5))
    course_name: Mapped[str] = mapped_column(VARCHAR(50))
    course_type: Mapped[str] = mapped_column(VARCHAR(10))
    credit: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(VARCHAR(12))
    score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    passed: Mapped[int | None] = mapped_column(Integer)
