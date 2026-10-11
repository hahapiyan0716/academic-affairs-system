"""
SQLAlchemy 2.0 ORM(Object-Relational Mapping) 模型 —— 資料庫結構的唯一來源(Single Source of Truth)。

修改資料表的流程：
  1. 修改本檔
  2. alembic revision --autogenerate -m "說明"   產生 migrations/versions/*.py
  3. 檢查產生的 migration（autogenerate 不會偵測 CHECK 約束與 View 的變更，需手動補上）
  4. alembic upgrade head                         套用到資料庫

命名慣例：資料表 PascalCase、欄位 snake_case，約束與索引名稱沿用最初由 Prisma 建立時的命名
(<表>_<欄位>_key / _idx / _fkey)，讓既有資料庫與本檔完全一致。

什麼是 ORM？
ORM 是 Object-Relational Mapping 的縮寫，意指「物件導向程式設計」與「關聯式資料庫」之間的對應關係。
ORM 讓開發者可以使用程式語言的物件來操作資料庫，而不需要直接撰寫 SQL 語句，因為後面的 SQLAlchemy 會自動處理 SQL 的生成和執行。
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


class Base(DeclarativeBase):    # DeclarativeBase 是一個基底類別，所有 ORM 模型都要繼承它，才能被 SQLAlchemy 辨識為資料表
    """所有 ORM 模型的基底；Base.metadata 收集全部資料表，供 Alembic 比對"""


# 所有資料表統一使用 utf8mb4_unicode_ci（MySQL 8 的預設 collation 是 utf8mb4_0900_ai_ci）
TABLE_OPTIONS: dict[str, Any] = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


# *items：可變長度的參數列表，允許傳入任意數量的索引或約束
# tuple[Any, ...]：表示回傳值是一個包含任意型別的元組，元組的長度不固定
def table_args(*items: Any) -> tuple[Any, ...]:
    """組出 __table_args__：約束與索引在前，最後附上共用的資料表選項（SQLAlchemy 規定 dict 必須放最後）"""
    return (*items, TABLE_OPTIONS)


# fk()：簡化 ForeignKey 的建立。ON UPDATE 一律 CASCADE（主鍵值被修改時，外鍵跟著更新）；
# ON DELETE 預設 RESTRICT（仍有子資料參照時拒絕刪除），需要連帶刪除時才傳 ondelete="CASCADE"
def fk(target: str, name: str, *, ondelete: str = "RESTRICT") -> ForeignKey:
    """外鍵一律 ON UPDATE CASCADE；ON DELETE 依關係決定"""
    return ForeignKey(target, name=name, ondelete=ondelete, onupdate="CASCADE")


# server_default 用的 SQL 片段：預設值寫進 DDL(Data Definition Language)，由資料庫產生，而不是由 Python 在 INSERT 時帶入
TRUE = text("1")
FALSE = text("0")
NOW = func.current_timestamp()


# ---------------------------------------------------------------------
# 列舉(Enum)型別：帳號角色、學籍狀態、課程類別、學期狀態、班級狀態、修課狀態
# ---------------------------------------------------------------------

class Role(StrEnum):
    """帳號角色：管理員、教師、學生"""

    Admin = "Admin"
    Teacher = "Teacher"
    Student = "Student"


class StudentStatus(StrEnum):
    """學籍狀態：在學、休學、退學"""

    Enrolled = "Enrolled"
    Suspended = "Suspended"
    Dropped = "Dropped"


class CourseType(StrEnum):
    """課程類別：必修、選修"""

    Required = "Required"
    Elective = "Elective"


class SemesterStatus(StrEnum):
    """規劃中（可開課）→ 選課中（可開課、可加退選）→ 上課中（可登分）→ 已結束（可登分）"""

    Planning = "Planning"
    Enrolling = "Enrolling"
    InProgress = "InProgress"
    Finished = "Finished"


class SectionStatus(StrEnum):
    """班級狀態：開課中、已停開"""

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


# 「實際佔用名額／實際修課」的狀態，也就是學生已經可以進入教室上課、老師也要負責評分的狀態
# 例如：學生加選成功（Selected）或人工加選（Manual）才算有效選課，落選（NotSelected）或退選（Withdrawn）都不算
ACTIVE_ENROLLMENT = (EnrollmentStatus.Selected, EnrollmentStatus.Manual)


# cls: type[StrEnum]：表示 cls 是 StrEnum 的子類別本身（傳入的是類別，例如 Role，而不是 Role.Admin 這種成員）
def _enum(cls: type[StrEnum]) -> Enum:
    """把 Python 列舉對應成資料庫欄位型別；資料庫中存的是列舉的值（value）而非名稱"""
    # native_enum=True 對應 MySQL 的 ENUM 型別
    # validate_strings 讓錯誤值在 Python 端就被擋下
    # values_callable=lambda e: [m.value for m in e] 讓資料庫欄位的選項對應到列舉的值，而不是名稱
    return Enum(cls, native_enum=True, validate_strings=True, values_callable=lambda e: [m.value for m in e])


# 以上都是在定義資料庫模型之前的設定與工具函式，接下來才是實際的資料表模型定義
# ---------------------------------------------------------------------
# 帳號與身分
# ---------------------------------------------------------------------


class UserAccount(Base):
    """系統登入帳號；Teacher / Student 透過 user_id 一對一連結，Admin 無對應的個人資料表"""

    __tablename__ = "UserAccount"
    __table_args__ = table_args(UniqueConstraint("username", name="UserAccount_username_key"))  # name：唯一約束的名稱（MySQL 以同名的唯一索引實作）

    # Mapped[int]：表示 user_id 是一個整數型別的欄位，並且會被映射到資料庫中的對應欄位
    # mapped_column(Integer, primary_key=True, autoincrement=True)：表示 user_id 是一個整數型別的欄位，並且是主鍵(primary key)，自動遞增(autoincrement)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(VARCHAR(30))
    password_hash: Mapped[str] = mapped_column(VARCHAR(100))  # bcrypt 雜湊，不存明碼
    role: Mapped[Role] = mapped_column(_enum(Role))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=TRUE)  # 停用的帳號無法登入
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=NOW)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    # 登入狀態的版本：JWT 帶有簽發當下的版本（ver），兩者不同即視為失效。
    # 修改或重設密碼時加 1，讓所有裝置上既有的登入立即失效
    token_version: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    # relationship()：手上有 account 時，用 account.teacher／account.student 直接取得對應物件，不必自己寫查詢。
    #   資料庫中沒有這兩個欄位，SQLAlchemy 依對方的 FK（Teacher.user_id／Student.user_id）自動推導 JOIN 條件。
    #   只是拿一個值篩選資料（WHERE）時用不到 relationship，直接比對欄位即可。
    # 用途：登入時取姓名與 teacher_id／student_id 寫進 JWT；管理員帳號列表顯示對應的教師／學生資料。
    # 一對一：型別是單一物件（不是 list），對方的 user_id 設有 UNIQUE 確保不重複；Admin 沒有對應資料，值為 None。
    # back_populates="user"：與 Teacher.user／Student.user 互相連動，設定其中一邊，另一邊自動對應（不必等 commit）。
    # "Teacher | None" 加引號：Teacher 定義在下方，先用字串表示型別。
    teacher: Mapped["Teacher | None"] = relationship(back_populates="user")
    student: Mapped["Student | None"] = relationship(back_populates="user")


class Department(Base):
    """系所"""

    __tablename__ = "Department"
    __table_args__ = table_args(UniqueConstraint("dept_name", name="Department_dept_name_key"))
    # name="Department_dept_name_key"：唯一約束的名稱（MySQL 以同名的唯一索引實作）

    dept_id: Mapped[str] = mapped_column(CHAR(4), primary_key=True)
    dept_name: Mapped[str] = mapped_column(VARCHAR(50))


class Teacher(Base):
    """教師個人資料；user_id 連結登入帳號（一對一）"""

    __tablename__ = "Teacher"
    __table_args__ = table_args(UniqueConstraint("user_id", name="Teacher_user_id_key"))

    teacher_id: Mapped[str] = mapped_column(CHAR(6), primary_key=True)
    # 原 3NF 設計為 UNIQUE，實務上教師姓名可能重複，故移除
    teacher_name: Mapped[str] = mapped_column(VARCHAR(50))
    dept_id: Mapped[str | None] = mapped_column(
        CHAR(4), fk("Department.dept_id", "Teacher_dept_id_fkey", ondelete="SET NULL")
    )
    # 開課權限：由管理員指派／收回。刻意不放進 JWT，每次開課請求都查資料庫確認，
    # 避免權限被收回後，在舊 JWT 到期前（JWT_EXPIRES_IN_HOURS，預設 8 小時）仍能開課
    can_open_section: Mapped[bool] = mapped_column(Boolean, server_default=FALSE)
    user_id: Mapped[int | None] = mapped_column(
        Integer, fk("UserAccount.user_id", "Teacher_user_id_fkey", ondelete="SET NULL")
    )

    user: Mapped[UserAccount | None] = relationship(back_populates="teacher")
    # Mapped[list["TeacherPermissionLog"]]：表示 permission_logs 是一個列表，裡面包含多個 TeacherPermissionLog 物件
    # relationship(back_populates="teacher")：表示 permission_logs 與 TeacherPermissionLog.teacher 之間是雙向關聯，在 Python 端設定其中一方時，另一方在記憶體中立即同步，不必等 commit
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
    # 執行這次權限變更的管理員 user_id（資料庫中實際存在的欄位）；寫入時直接填 JWT 的 sub，不必先查出帳號物件。
    # 未傳 ondelete，預設 RESTRICT：有稽核紀錄的帳號無法刪除，確保事後能追查操作者；不再使用的帳號應改為停用（is_active）。
    changed_by: Mapped[int] = mapped_column(
        Integer, fk("UserAccount.user_id", "TeacherPermissionLog_changed_by_fkey")
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=NOW)

    # relationship()：ORM 層的關聯（資料庫中不會產生此欄位），依 TeacherPermissionLog.teacher_id 的 FK 自動推導 JOIN 條件。
    teacher: Mapped[Teacher] = relationship(back_populates="permission_logs")
    # admin：依 changed_by 的 FK 自動推導 JOIN 條件（TeacherPermissionLog.changed_by = UserAccount.user_id），
    # 讀取時以 log.admin.username 取得操作者帳號名稱（回應模型為 schemas/teacher_schema.py 的 AdminRefOut）。
    # relationship 的名稱(admin)不必與 FK 欄位(changed_by)相同，SQLAlchemy 依 FK 配對而非名稱。
    # 單向關聯（沒有 back_populates）：UserAccount 不需要「列出某管理員的所有操作」，因此不在對方加對應屬性。
    admin: Mapped[UserAccount] = relationship()


class Student(Base):
    """學生學籍資料；user_id 連結登入帳號（一對一）"""

    __tablename__ = "Student"
    __table_args__ = table_args(UniqueConstraint("user_id", name="Student_user_id_key"))

    student_id: Mapped[str] = mapped_column(CHAR(10), primary_key=True)
    student_name: Mapped[str] = mapped_column(VARCHAR(30))
    dept_id: Mapped[str] = mapped_column(CHAR(4), fk("Department.dept_id", "Student_dept_id_fkey"))
    grade: Mapped[int] = mapped_column(TINYINT)  # 年級
    status: Mapped[StudentStatus] = mapped_column(_enum(StudentStatus))
    class_code: Mapped[str] = mapped_column(CHAR(2))  # 班別
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
    """建築物"""

    __tablename__ = "Building"
    __table_args__ = table_args(UniqueConstraint("building_name", name="Building_building_name_key"))

    building_id: Mapped[str] = mapped_column(CHAR(4), primary_key=True)
    building_name: Mapped[str] = mapped_column(VARCHAR(50))


class Room(Base):
    """教室；seat_capacity 為座位數（未知時為 NULL）"""

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
    """課程（課號、名稱、學分）；每學期實際開設的班級見 Section"""

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
    # course.fields：有一門課，要知道它屬於哪些領域；課程列表顯示領域、編輯課程時整批替換領域都經由它。
    # 只建立這個方向：反方向（cf.course，有一筆 CurriculumField 要拿回課程）程式中沒有需要，說明見 CurriculumField。
    # delete-orphan：從 fields 清單移除的項目，flush 時會從資料庫刪除
    fields: Mapped[list["CurriculumField"]] = relationship(
        cascade="all, delete-orphan", order_by="CurriculumField.field_name"
    )


class CurriculumField(Base):
    """課程所屬的領域（一門課可屬於多個領域）；以 (course_no, field_name) 為複合主鍵"""

    __tablename__ = "CurriculumField"
    __table_args__ = table_args()

    course_no: Mapped[str] = mapped_column(
        CHAR(5), fk("Course.course_no", "CurriculumField_course_no_fkey", ondelete="CASCADE"), primary_key=True
    )
    field_name: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True)

    # 不建立反向 relationship（cf.course）：程式只會從 Course 讀取領域（Course.fields），不會從單筆 CurriculumField 回頭找課程。
    # 依領域篩選屬於查詢條件，直接以欄位比對即可（見 section_repository._has_field 的 EXISTS 子查詢），不需要 relationship。


# ---------------------------------------------------------------------
# 學期與開課班級
# ---------------------------------------------------------------------


class Semester(Base):
    """學期；status 決定此學期目前可進行的操作（見 SemesterStatus）"""

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
        # 同一門課在同一學期的班別不可重複（例如不能有兩個 01 班）
        UniqueConstraint(
            "course_no", "semester_id", "section_code", name="Section_course_no_semester_id_section_code_key"
        ),
        # 供 SectionSchedule 的複合外鍵參照，確保時段的 semester_id 與班級一致
        UniqueConstraint("section_id", "semester_id", name="Section_section_id_semester_id_key"),
        # 加速「某學期＋某狀態」的班級查詢（如選課頁列出開課中的班級）；也作為 semester_id 外鍵所需的索引
        Index("Section_semester_id_status_idx", "semester_id", "status"),
        CheckConstraint("capacity BETWEEN 1 AND 500", name="chk_section_capacity"),
    )

    section_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_no: Mapped[str] = mapped_column(CHAR(5), fk("Course.course_no", "Section_course_no_fkey"))
    semester_id: Mapped[str] = mapped_column(CHAR(4), fk("Semester.semester_id", "Section_semester_id_fkey"))
    section_code: Mapped[str] = mapped_column(CHAR(2), server_default="01")  # 班別：同課同學期的第幾班
    capacity: Mapped[int] = mapped_column(SmallInteger)  # 修課人數上限
    status: Mapped[SectionStatus] = mapped_column(_enum(SectionStatus), server_default="Open")
    # 由哪位教師建立（系統匯入的歷史資料可為 NULL）
    created_by: Mapped[str | None] = mapped_column(
        CHAR(6), fk("Teacher.teacher_id", "Section_created_by_fkey", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=NOW)

    # relationship()：用 section.semester 取代自己寫 db.get(Semester, section.semester_id)，省的是程式碼，不是查詢次數。
    #   預設為 lazy loading：存取 section.semester 時才另發一句 SELECT 查 Semester 表。
    #   同一個 Session 內，同一筆資料只會查一次、只有一個物件（Identity Map）：
    #   兩個班級都屬於 1151 學期時，a.semester is b.semester，第二次存取不再查詢。
    #   這是 Session 的功能，與有沒有 relationship 無關。
    #   一次處理多個班級時，改用 selectinload 預先載入，避免每個班級各查一次（N+1 問題）。
    course: Mapped[Course] = relationship()
    semester: Mapped[Semester] = relationship()
    # Mapped[...] 是 SQLAlchemy ORM 的型別標註，表示此屬性由 SQLAlchemy 管理，以及讀取時預期得到的型別。
    # list[...] 代表這個屬性會取得多個物件；"SectionTeacher" 加引號是因為該類別定義在下方，避免尚未定義就被解析。
    # 一個班級可以有多位教師
    # cascade="all, delete-orphan" 表示當 Section 被刪除時，其關聯的 SectionTeacher 紀錄也會被刪除。
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
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default=TRUE)  # 主授教師（列表中排在前面）

    section: Mapped[Section] = relationship(back_populates="teachers")
    # Mapped[Teacher] 表示此屬性會取得單一 Teacher 物件；Teacher 已在上方定義，所以不必寫成字串 "Teacher"。
    # 冒號後的 Mapped[Teacher] 負責型別標註，等號右側的 relationship() 才負責設定 ORM 關聯。
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

        # 防止「同班級、同星期、同時段」重複上課
        UniqueConstraint("section_id", "weekday", "period", name="SectionSchedule_section_id_weekday_period_key"),
        # 資料庫層防止「同學期、同教室、同時段」重複借用（含併發開課的競態）
        UniqueConstraint("semester_id", "room_code", "weekday", "period", name="uq_room_timeslot"),
        Index("SectionSchedule_room_code_idx", "room_code"),
        # 檢查星期的範圍
        CheckConstraint("weekday BETWEEN 1 AND 7", name="chk_schedule_weekday"),
        # 檢查節次的範圍
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
    score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))  # 學期成績（0–100，一位小數）；NULL 表示尚未登分
    feedback_rank: Mapped[int | None] = mapped_column(TINYINT)  # 教學評量（1–10）
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, server_default=NOW)
    # onupdate：透過 ORM 更新這一列時，SQLAlchemy 自動把此欄設為目前時間
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
# View 是一種特殊的資料表，它不儲存實際的資料，而是根據其他資料表的內容動態產生。
# ---------------------------------------------------------------------


class SectionDetailView(Base):
    """
    班級明細：班級 + 課程資訊，並把多筆子資料彙整成單一欄位
    - teacher_names：授課教師（主授在前，以「、」分隔）
    - schedule_text：上課時段，例如 "一5@A101,三3@B203"
    - enrolled_count：有效選課（Selected／Manual）人數
    """

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
    """
    學生歷年成績單：只含有效選課（Selected／Manual）的紀錄
    passed：1 = 及格、0 = 不及格、NULL = 尚未登分；大學部 60 分及格、碩博班 70 分及格
    """

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
