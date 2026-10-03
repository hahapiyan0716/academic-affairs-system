"""認證與管理員 API 的 Pydantic 模型"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.security import PASSWORD_MAX_BYTES


def _password_bytes(value: str) -> str:
    # bcrypt 只接受 72 bytes 以內；中文一字佔 3 bytes，因此以 bytes 而非字元數限制
    if len(value.encode()) > PASSWORD_MAX_BYTES:
        raise ValueError(f"密碼過長（上限 {PASSWORD_MAX_BYTES} bytes）")
    return value


Password = Annotated[str, Field(min_length=8, max_length=72), AfterValidator(_password_bytes)]
Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=30)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------
# 認證
# ---------------------------------------------------------------------


class LoginIn(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    password: str = Field(min_length=1, max_length=100)


# ---------------------------------------------------------------------
# 帳號
# ---------------------------------------------------------------------


class TeacherProfileIn(BaseModel):
    teacher_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6)]
    teacher_name: Name
    dept_id: str | None = Field(default=None, min_length=4, max_length=4)


class StudentProfileIn(BaseModel):
    student_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
    student_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    dept_id: str = Field(min_length=4, max_length=4)
    grade: int = Field(ge=1, le=7)
    class_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2)]
    degree: Literal[0, 1] = 0


class AdminCreateIn(BaseModel):
    role: Literal["Admin"]
    username: Username
    password: Password


class TeacherCreateIn(BaseModel):
    role: Literal["Teacher"]
    username: Username
    password: Password
    profile: TeacherProfileIn


class StudentCreateIn(BaseModel):
    role: Literal["Student"]
    username: Username
    password: Password
    profile: StudentProfileIn


# 依 role 欄位決定要套用哪一個模型（discriminated union）
UserCreateIn = Annotated[AdminCreateIn | TeacherCreateIn | StudentCreateIn, Field(discriminator="role")]


class UserUpdateIn(BaseModel):
    is_active: bool | None = None
    password: Password | None = None


class StudentStatusIn(BaseModel):
    status: Literal["Enrolled", "Suspended", "Dropped"]


class UserTeacherOut(ORMModel):
    teacher_id: str
    teacher_name: str
    can_open_section: bool


class UserStudentOut(ORMModel):
    student_id: str
    student_name: str
    dept_id: str
    status: str


class UserOut(ORMModel):
    user_id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    teacher: UserTeacherOut | None
    student: UserStudentOut | None


# ---------------------------------------------------------------------
# 教師開課權限
# ---------------------------------------------------------------------


class PermissionIn(BaseModel):
    can_open_section: bool


class AdminRefOut(ORMModel):
    username: str


class PermissionLogOut(ORMModel):
    log_id: int
    granted: bool
    changed_at: datetime
    admin: AdminRefOut


class TeacherUserOut(ORMModel):
    username: str
    is_active: bool


class AdminTeacherOut(ORMModel):
    teacher_id: str
    teacher_name: str
    dept_id: str | None
    can_open_section: bool
    user: TeacherUserOut | None
    latest_log: PermissionLogOut | None


class TeacherOut(ORMModel):
    teacher_id: str
    teacher_name: str
    dept_id: str | None
    can_open_section: bool


# ---------------------------------------------------------------------
# 課程庫
# ---------------------------------------------------------------------

FieldNames = Annotated[list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]], Field(max_length=10)]


class CourseCreateIn(BaseModel):
    course_no: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=5)]
    course_name: Name
    course_type: Literal["Required", "Elective"]
    credit: int = Field(ge=0, le=10)
    dept_id: str | None = Field(default=None, min_length=4, max_length=4)
    fields: FieldNames = []


class CourseUpdateIn(BaseModel):
    course_name: Name | None = None
    course_type: Literal["Required", "Elective"] | None = None
    credit: int | None = Field(default=None, ge=0, le=10)
    dept_id: str | None = Field(default=None, min_length=4, max_length=4)
    is_active: bool | None = None
    # 有傳入時整批取代
    fields: FieldNames | None = None


class AdminCourseOut(BaseModel):
    course_no: str
    course_name: str
    course_type: str
    credit: int
    dept_id: str | None
    dept_name: str | None
    is_active: bool
    fields: list[str]
    section_count: int


# ---------------------------------------------------------------------
# 學期
# ---------------------------------------------------------------------


class SemesterCreateIn(BaseModel):
    acad_year: int = Field(ge=100, le=999)
    term: int = Field(ge=1, le=3)


class SemesterUpdateIn(BaseModel):
    status: Literal["Planning", "Enrolling", "InProgress", "Finished"] | None = None
    # 只能「設為目前學期」；其他學期的旗標會在同一個交易內清除
    is_current: Literal[True] | None = None


class AdminSemesterOut(BaseModel):
    semester_id: str
    acad_year: int
    term: int
    status: str
    is_current: bool
    section_count: int


class StatsOut(BaseModel):
    users: int
    teachers_with_permission: int
    enrolled_students: int
    active_courses: int
    current_semester: AdminSemesterOut | None


class DepartmentOut(ORMModel):
    dept_id: str
    dept_name: str
