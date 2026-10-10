"""
SQLAlchemy 2.0 ORM 模型 —— 資料庫結構的唯一來源（Single Source of Truth）。

修改資料表的流程：
  1. 修改本檔
  2. alembic revision --autogenerate -m "說明"   產生 migrations/versions/*.py
  3. 檢查產生的 migration（autogenerate 不會偵測 CHECK 約束與 View 的變更，需手動補上）
  4. alembic upgrade head                         套用到資料庫

命名慣例：資料表 PascalCase、欄位 snake_case；約束與索引名稱沿用最初由 Prisma 建立時的命名
（<表>_<欄位>_key / _idx / _fkey），讓既有資料庫與本檔完全一致。
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CHAR,
    DECIMAL,
    VARCHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# 所有資料表統一使用 utf8mb4_unicode_ci（MySQL 8 的預設 collation 是 utf8mb4_0900_ai_ci）
TABLE_OPTIONS: dict[str, Any] = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


def table_args(*items: Any) -> tuple[Any, ...]:
    return (*items, TABLE_OPTIONS)


def fk(target: str, name: str, *, ondelete: str = "RESTRICT") -> ForeignKey:
    """外鍵一律 ON UPDATE CASCADE；ON DELETE 依關係決定"""
    return ForeignKey(target, name=name, ondelete=ondelete, onupdate="CASCADE")


TRUE = text("1")
FALSE = text("0")
NOW = func.current_timestamp()


# ---------------------------------------------------------------------
# 列舉
# ---------------------------------------------------------------------


class Role(StrEnum):
    Admin = "Admin"
    Teacher = "Teacher"
    Student = "Student"


class StudentStatus(StrEnum):
    """學籍狀態：在學、休學、退學"""

    Enrolled = "Enrolled"
    Suspended = "Suspended"
    Dropped = "Dropped"


class CourseType(StrEnum):
    Required = "Required"
    Elective = "Elective"


class SemesterStatus(StrEnum):
    """規劃中（可開課）→ 選課中（可開課、可加退選）→ 上課中（可登分）→ 已結束（可登分）"""

    Planning = "Planning"
    Enrolling = "Enrolling"
    InProgress = "InProgress"
    Finished = "Finished"


class SectionStatus(StrEnum):
    Open = "Open"
    Cancelled = "Cancelled"


class EnrollmentStatus(StrEnum):
    """
    Registered  ：已登記、待分發（預留給未來的「登記 + 隨機分發」機制）
    Selected    ：中選（先搶先贏模式下加選成功即為此狀態）
    Manual      ：人工加選
    NotSelected ：落選（對應原 3NF 資料的 'Dropped'）
    Withdrawn   ：學生自行退選
    """

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
# 帳號與身分
# ---------------------------------------------------------------------


class UserAccount(Base):
    """系統登入帳號；Teacher / Student 透過 user_id 一對一連結，Admin 無對應的個人資料表"""

    __tablename__ = "UserAccount"
    __table_args__ = table_args(UniqueConstraint("username", name="UserAccount_username_key"))

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(VARCHAR(30))
    password_hash: Mapped[str] = mapped_column(VARCHAR(100))
    role: Mapped[Role] = mapped_column(_enum(Role))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=TRUE)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=NOW)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    teacher: Mapped["Teacher | None"] = relationship(back_populates="user")
    student: Mapped["Student | None"] = relationship(back_populates="user")


class Department(Base):
    __tablename__ = "Department"
    __table_args__ = table_args(UniqueConstraint("dept_name", name="Department_dept_name_key"))

    dept_id: Mapped[str] = mapped_column(CHAR(4), primary_key=True)
    dept_name: Mapped[str] = mapped_column(VARCHAR(50))


class Teacher(Base):
    __tablename__ = "Teacher"
    __table_args__ = table_args(UniqueConstraint("user_id", name="Teacher_user_id_key"))

    teacher_id: Mapped[str] = mapped_column(CHAR(6), primary_key=True)
    # 原 3NF 設計為 UNIQUE，實務上教師姓名可能重複，故移除
    teacher_name: Mapped[str] = mapped_column(VARCHAR(50))
    dept_id: Mapped[str | None] = mapped_column(
        CHAR(4), fk("Department.dept_id", "Teacher_dept_id_fkey", ondelete="SET NULL")
    )
    # 開課權限：由管理員指派／收回；刻意不放進 JWT，每次開課都查資料庫
    can_open_section: Mapped[bool] = mapped_column(Boolean, server_default=FALSE)
    user_id: Mapped[int | None] = mapped_column(
        Integer, fk("UserAccount.user_id", "Teacher_user_id_fkey", ondelete="SET NULL")
    )

    user: Mapped[UserAccount | None] = relationship(back_populates="teacher")
    permission_logs: Mapped[list["TeacherPermissionLog"]] = relationship(
        back_populates="teacher", order_by=lambda: TeacherPermissionLog.changed_at.desc()
    )


class TeacherPermissionLog(Base):
    """開課權限切換的稽核紀錄（誰、何時、授予或收回）"""

    __tablename__ = "TeacherPermissionLog"
    __table_args__ = table_args(
        Index("TeacherPermissionLog_teacher_id_changed_at_idx", "teacher_id", "changed_at"),
    )

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[str] = mapped_column(
        CHAR(6), fk("Teacher.teacher_id", "TeacherPermissionLog_teacher_id_fkey")
    )
    granted: Mapped[bool] = mapped_column(Boolean)
    changed_by: Mapped[int] = mapped_column(
        Integer, fk("UserAccount.user_id", "TeacherPermissionLog_changed_by_fkey")
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=NOW)

    teacher: Mapped[Teacher] = relationship(back_populates="permission_logs")
    admin: Mapped[UserAccount] = relationship()


class Student(Base):
    __tablename__ = "Student"
    __table_args__ = table_args(UniqueConstraint("user_id", name="Student_user_id_key"))

    student_id: Mapped[str] = mapped_column(CHAR(10), primary_key=True)
    student_name: Mapped[str] = mapped_column(VARCHAR(30))
    dept_id: Mapped[str] = mapped_column(CHAR(4), fk("Department.dept_id", "Student_dept_id_fkey"))
    grade: Mapped[int] = mapped_column(TINYINT)
    status: Mapped[StudentStatus] = mapped_column(_enum(StudentStatus))
    class_code: Mapped[str] = mapped_column(CHAR(2))
    # 0 = 大學部、1 = 碩博班（影響及格標準：60 / 70）
    degree: Mapped[int] = mapped_column(TINYINT, server_default=text("0"))
    user_id: Mapped[int | None] = mapped_column(
        Integer, fk("UserAccount.user_id", "Student_user_id_fkey", ondelete="SET NULL")
    )

    user: Mapped[UserAccount | None] = relationship(back_populates="student")


# ---------------------------------------------------------------------
# 校園空間
# ---------------------------------------------------------------------


class Building(Base):
    __tablename__ = "Building"
    __table_args__ = table_args(UniqueConstraint("building_name", name="Building_building_name_key"))

    building_id: Mapped[str] = mapped_column(CHAR(4), primary_key=True)
    building_name: Mapped[str] = mapped_column(VARCHAR(50))


class Room(Base):
    __tablename__ = "Room"
    __table_args__ = table_args()

    room_code: Mapped[str] = mapped_column(VARCHAR(10), primary_key=True)
    building_id: Mapped[str] = mapped_column(CHAR(4), fk("Building.building_id", "Room_building_id_fkey"))
    seat_capacity: Mapped[int | None] = mapped_column(SmallInteger)

    building: Mapped[Building] = relationship()


# ---------------------------------------------------------------------
# 課程庫（跨學期不變的資訊）
# ---------------------------------------------------------------------


class Course(Base):
    __tablename__ = "Course"
    __table_args__ = table_args(CheckConstraint("credit BETWEEN 0 AND 10", name="chk_course_credit"))

    course_no: Mapped[str] = mapped_column(CHAR(5), primary_key=True)
    course_name: Mapped[str] = mapped_column(VARCHAR(50))
    course_type: Mapped[CourseType] = mapped_column(_enum(CourseType))
    credit: Mapped[int] = mapped_column(TINYINT)
    dept_id: Mapped[str | None] = mapped_column(
        CHAR(4), fk("Department.dept_id", "Course_dept_id_fkey", ondelete="SET NULL")
    )
    # 停用的課程不可再開新班，但歷史班級仍保留
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=TRUE)

    department: Mapped[Department | None] = relationship()
    fields: Mapped[list["CurriculumField"]] = relationship(
        cascade="all, delete-orphan", order_by="CurriculumField.field_name"
    )


class CurriculumField(Base):
    __tablename__ = "CurriculumField"
    __table_args__ = table_args()

    course_no: Mapped[str] = mapped_column(
        CHAR(5), fk("Course.course_no", "CurriculumField_course_no_fkey", ondelete="CASCADE"), primary_key=True
    )
    field_name: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True)


# ---------------------------------------------------------------------
# 學期與開課班級
# ---------------------------------------------------------------------


class Semester(Base):
    __tablename__ = "Semester"
    __table_args__ = table_args(
        UniqueConstraint("acad_year", "term", name="Semester_acad_year_term_key"),
        CheckConstraint("term IN (1, 2, 3)", name="chk_semester_term"),
    )

    # 民國學年 + 學期，例如 '1132' = 113 學年度第 2 學期
    semester_id: Mapped[str] = mapped_column(CHAR(4), primary_key=True)
    acad_year: Mapped[int] = mapped_column(SmallInteger)
    term: Mapped[int] = mapped_column(TINYINT)
    status: Mapped[SemesterStatus] = mapped_column(_enum(SemesterStatus), server_default="Planning")
    # 「目前學期」，同一時間僅允許一筆為 true（由應用層在交易中維護）
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=FALSE)


class Section(Base):
    """開課班級：某門課在某學期的一次開設"""

    __tablename__ = "Section"
    __table_args__ = table_args(
        UniqueConstraint(
            "course_no", "semester_id", "section_code", name="Section_course_no_semester_id_section_code_key"
        ),
        # 供 SectionSchedule 的複合外鍵參照，確保時段的 semester_id 與班級一致
        UniqueConstraint("section_id", "semester_id", name="Section_section_id_semester_id_key"),
        Index("Section_semester_id_status_idx", "semester_id", "status"),
        CheckConstraint("capacity BETWEEN 1 AND 500", name="chk_section_capacity"),
    )

    section_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_no: Mapped[str] = mapped_column(CHAR(5), fk("Course.course_no", "Section_course_no_fkey"))
    semester_id: Mapped[str] = mapped_column(CHAR(4), fk("Semester.semester_id", "Section_semester_id_fkey"))
    section_code: Mapped[str] = mapped_column(CHAR(2), server_default="01")
    capacity: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[SectionStatus] = mapped_column(_enum(SectionStatus), server_default="Open")
    # 由哪位教師建立（系統匯入的歷史資料可為 NULL）
    created_by: Mapped[str | None] = mapped_column(
        CHAR(6), fk("Teacher.teacher_id", "Section_created_by_fkey", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=NOW)

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
    """開課班級與授課教師的多對多關係（一班可多位教師合授）"""

    __tablename__ = "SectionTeacher"
    __table_args__ = table_args(Index("SectionTeacher_teacher_id_idx", "teacher_id"))

    section_id: Mapped[int] = mapped_column(
        Integer, fk("Section.section_id", "SectionTeacher_section_id_fkey", ondelete="CASCADE"), primary_key=True
    )
    teacher_id: Mapped[str] = mapped_column(
        CHAR(6), fk("Teacher.teacher_id", "SectionTeacher_teacher_id_fkey"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default=TRUE)

    section: Mapped[Section] = relationship(back_populates="teachers")
    teacher: Mapped[Teacher] = relationship()


class SectionSchedule(Base):
    """單一上課時段；原 time_slot '一5' 拆為 weekday = 1、period = 5"""

    __tablename__ = "SectionSchedule"
    __table_args__ = table_args(
        ForeignKeyConstraint(
            ["section_id", "semester_id"],
            ["Section.section_id", "Section.semester_id"],
            name="SectionSchedule_section_id_semester_id_fkey",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        UniqueConstraint("section_id", "weekday", "period", name="SectionSchedule_section_id_weekday_period_key"),
        # 資料庫層防止「同學期、同教室、同時段」重複借用（含併發開課的競態）
        UniqueConstraint("semester_id", "room_code", "weekday", "period", name="uq_room_timeslot"),
        Index("SectionSchedule_room_code_idx", "room_code"),
        CheckConstraint("weekday BETWEEN 1 AND 7", name="chk_schedule_weekday"),
        CheckConstraint("period BETWEEN 1 AND 14", name="chk_schedule_period"),
    )

    schedule_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(Integer)
    # 刻意冗餘的學期欄位：透過複合外鍵保證與班級一致，讓上方的 uq_room_timeslot 得以成立
    semester_id: Mapped[str] = mapped_column(CHAR(4))
    room_code: Mapped[str] = mapped_column(VARCHAR(10), fk("Room.room_code", "SectionSchedule_room_code_fkey"))
    weekday: Mapped[int] = mapped_column(TINYINT)  # 1 = 星期一 … 7 = 星期日
    period: Mapped[int] = mapped_column(TINYINT)  # 節次

    section: Mapped[Section] = relationship(back_populates="schedules")


# ---------------------------------------------------------------------
# 選課與成績
# ---------------------------------------------------------------------


class Enrollment(Base):
    """取代原 CourseSelection；學期資訊由 section 推得，不再重複儲存"""

    __tablename__ = "Enrollment"
    __table_args__ = table_args(
        Index("Enrollment_section_id_status_idx", "section_id", "status"),
        CheckConstraint("score IS NULL OR score BETWEEN 0 AND 100", name="chk_enrollment_score"),
        CheckConstraint("feedback_rank IS NULL OR feedback_rank BETWEEN 1 AND 10", name="chk_enrollment_feedback"),
    )

    student_id: Mapped[str] = mapped_column(
        CHAR(10), fk("Student.student_id", "Enrollment_student_id_fkey"), primary_key=True
    )
    section_id: Mapped[int] = mapped_column(
        Integer, fk("Section.section_id", "Enrollment_section_id_fkey"), primary_key=True
    )
    status: Mapped[EnrollmentStatus] = mapped_column(_enum(EnrollmentStatus))
    score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    feedback_rank: Mapped[int | None] = mapped_column(TINYINT)  # 教學評量（1–10）
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, server_default=NOW)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=NOW, onupdate=func.now())

    student: Mapped[Student] = relationship()
    section: Mapped[Section] = relationship()


class ScoreChangeLog(Base):
    """成績修改稽核紀錄"""

    __tablename__ = "ScoreChangeLog"
    __table_args__ = table_args(
        ForeignKeyConstraint(
            ["student_id", "section_id"],
            ["Enrollment.student_id", "Enrollment.section_id"],
            name="ScoreChangeLog_student_id_section_id_fkey",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        Index("ScoreChangeLog_student_id_section_id_idx", "student_id", "section_id"),
    )

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(CHAR(10))
    section_id: Mapped[int] = mapped_column(Integer)
    old_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    new_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    changed_by: Mapped[int] = mapped_column(Integer, fk("UserAccount.user_id", "ScoreChangeLog_changed_by_fkey"))
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=NOW)


# ---------------------------------------------------------------------
# View（唯讀）：由 migrations/versions/ 以 CREATE VIEW 建立（目前的定義在 0002_field_names.py）
# info={"is_view": True} 讓 Alembic autogenerate 略過它們（見 migrations/env.py）
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
    field_names: Mapped[str | None] = mapped_column(VARCHAR(500))  # 課程領域，以「、」串接


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
    field_names: Mapped[str | None] = mapped_column(VARCHAR(500))
