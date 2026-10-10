"""帳號管理"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.auth_schema import Password, Username
from app.schemas.base import Name, ORMModel


class TeacherProfileIn(BaseModel):
    """建立教師帳號時一併建立的教師資料"""

    teacher_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6)]
    teacher_name: Name
    dept_id: str | None = Field(default=None, min_length=4, max_length=4)


class StudentProfileIn(BaseModel):
    """建立學生帳號時一併建立的學籍資料"""

    student_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
    student_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    dept_id: str = Field(min_length=4, max_length=4)
    grade: int = Field(ge=1, le=7)
    class_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2)]
    degree: Literal[0, 1] = 0  # 0 = 大學部、1 = 碩博班


class AdminCreateIn(BaseModel):
    """建立管理員帳號（沒有個人資料表）"""

    role: Literal["Admin"]
    username: Username
    password: Password


class TeacherCreateIn(BaseModel):
    """建立教師帳號，同時建立教師資料"""

    role: Literal["Teacher"]
    username: Username
    password: Password
    profile: TeacherProfileIn


class StudentCreateIn(BaseModel):
    """建立學生帳號，同時建立學籍資料"""

    role: Literal["Student"]
    username: Username
    password: Password
    profile: StudentProfileIn


# 依 role 欄位決定要套用哪一個模型（discriminated union）
UserCreateIn = Annotated[AdminCreateIn | TeacherCreateIn | StudentCreateIn, Field(discriminator="role")]


class UserUpdateIn(BaseModel):
    """管理員啟用／停用帳號或重設密碼；只更新有傳入的欄位"""

    is_active: bool | None = None
    password: Password | None = None


class StudentStatusIn(BaseModel):
    """管理員變更學籍狀態"""

    status: Literal["Enrolled", "Suspended", "Dropped"]


class StudentStatusOut(ORMModel):
    """變更後的學籍狀態"""

    student_id: str
    status: str


class UserTeacherOut(ORMModel):
    """帳號列表中附帶的教師資料"""

    teacher_id: str
    teacher_name: str
    can_open_section: bool


class UserStudentOut(ORMModel):
    """帳號列表中附帶的學生資料"""

    student_id: str
    student_name: str
    dept_id: str
    status: str


class UserOut(ORMModel):
    """帳號；teacher／student 依角色只有一個有值（Admin 兩者皆為 None）"""

    user_id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    teacher: UserTeacherOut | None
    student: UserStudentOut | None
