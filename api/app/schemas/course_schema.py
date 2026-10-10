"""課程庫"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.base import Name, ORMModel

# 課程領域名稱清單：每個名稱 1–50 字，一門課最多 10 個領域
FieldNames = Annotated[
    list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]],
    Field(max_length=10),
]


class CourseCreateIn(BaseModel):
    """管理員新增課程；課號固定 5 碼"""

    course_no: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=5)]
    course_name: Name
    course_type: Literal["Required", "Elective"]
    credit: int = Field(ge=0, le=10)
    dept_id: str | None = Field(default=None, min_length=4, max_length=4)
    fields: FieldNames = []


class CourseUpdateIn(BaseModel):
    """管理員修改課程；只更新有傳入（非 None）的欄位，課號不可修改"""

    course_name: Name | None = None
    course_type: Literal["Required", "Elective"] | None = None
    credit: int | None = Field(default=None, ge=0, le=10)
    dept_id: str | None = Field(default=None, min_length=4, max_length=4)
    is_active: bool | None = None
    # 有傳入時整批取代
    fields: FieldNames | None = None


class AdminCourseOut(BaseModel):
    """管理員的課程列表：含領域、系所名稱與歷年開班次數"""

    course_no: str
    course_name: str
    course_type: str
    credit: int
    dept_id: str | None
    dept_name: str | None
    is_active: bool
    fields: list[str]
    section_count: int


class CourseOut(ORMModel):
    """下拉選單用（教師開課時挑選課程）"""

    course_no: str
    course_name: str
    course_type: str
    credit: int
