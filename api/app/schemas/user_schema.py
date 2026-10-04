"""帳號管理"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.auth_schema import Password, Username
from app.schemas.base import Name, ORMModel


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


class StudentStatusOut(ORMModel):
    student_id: str
    status: str


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
