"""
測試共用設定。

測試直接連 .env 中的資料庫，但所有資料都建立在專用的測試學期 '9991'（999 學年第 1 學期），
每個測試結束後只刪除該學期底下的資料，不影響種子資料。
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.middleware.rate_limit import login_limiter
from app.session import CurrentUser, create_token
from app.models import (
    Enrollment,
    ScoreChangeLog,
    Section,
    SectionSchedule,
    SectionTeacher,
    Semester,
    SemesterStatus,
    Teacher,
)

TEST_SEMESTER = "9991"


def _cleanup() -> None:
    """刪除測試學期及其底下所有資料；順序為子表 → 父表，以免違反外鍵約束"""
    with SessionLocal() as db:
        section_ids = select(Section.section_id).where(Section.semester_id == TEST_SEMESTER)
        db.execute(delete(ScoreChangeLog).where(ScoreChangeLog.section_id.in_(section_ids)))
        db.execute(delete(Enrollment).where(Enrollment.section_id.in_(section_ids)))
        db.execute(delete(SectionSchedule).where(SectionSchedule.semester_id == TEST_SEMESTER))
        db.execute(delete(SectionTeacher).where(SectionTeacher.section_id.in_(section_ids)))
        db.execute(delete(Section).where(Section.semester_id == TEST_SEMESTER))
        db.execute(delete(Semester).where(Semester.semester_id == TEST_SEMESTER))
        db.commit()


@pytest.fixture
def semester() -> Iterator[Callable[[SemesterStatus], None]]:
    """建立測試學期（預設為選課中），回傳可切換學期狀態的函式"""
    # 先清一次：上次測試若中途被中斷，可能留下殘餘資料
    _cleanup()
    with SessionLocal() as db:
        db.add(Semester(semester_id=TEST_SEMESTER, acad_year=999, term=1, status=SemesterStatus.Enrolling))
        db.commit()

    def set_status(status: SemesterStatus) -> None:
        with SessionLocal() as db:
            db.get_one(Semester, TEST_SEMESTER).status = status
            db.commit()

    # yield 之前是 setup、之後是 teardown；測試失敗時 teardown 仍會執行
    yield set_status
    _cleanup()


# 依賴 semester fixture：班級一定建在測試學期中，並隨它一起被清除
@pytest.fixture
def make_section(semester) -> Callable[..., int]:
    """建立測試用班級，slots 格式為 [(weekday, period, room_code), ...]"""

    def factory(
        course_no: str = "A0001",
        capacity: int = 10,
        slots: list[tuple[int, int, str]] | None = None,
        teacher_id: str = "T001",
        section_code: str = "01",
    ) -> int:
        with SessionLocal() as db:
            section = Section(
                course_no=course_no,
                semester_id=TEST_SEMESTER,
                section_code=section_code,
                capacity=capacity,
                teachers=[SectionTeacher(teacher_id=teacher_id, is_primary=True)],
                schedules=[
                    SectionSchedule(weekday=w, period=p, room_code=r) for w, p, r in (slots or [(1, 1, "O313")])
                ],
            )
            db.add(section)
            db.commit()
            return section.section_id

    return factory


def _user_id(username: str) -> int:
    """查詢種子帳號的 user_id（JWT 的 sub 必須是真實存在的帳號）"""
    with SessionLocal() as db:
        return db.execute(text("SELECT user_id FROM UserAccount WHERE username = :u"), {"u": username}).scalar_one()


def make_token(username: str, role: str, *, teacher_id: str | None = None, student_id: str | None = None) -> str:
    """以正式程式碼的 create_token 簽發 JWT，省去每個測試都走一次登入流程"""
    user = CurrentUser(
        user_id=_user_id(username),
        username=username,
        role=role,  # type: ignore[arg-type]
        name=username,
        teacher_id=teacher_id,
        student_id=student_id,
    )
    return create_token(user)


@pytest.fixture(autouse=True)
def _reset_login_limiter() -> None:
    """登入限流的計數存在記憶體中，每個測試前清空，避免測試之間互相影響"""
    login_limiter.reset()


@pytest.fixture
def client_as() -> Callable[..., TestClient]:
    """以指定身分登入的 TestClient：client_as('S001')、client_as('T001', role='Teacher')"""

    def factory(username: str, role: str = "Student") -> TestClient:
        client = TestClient(app)
        token = make_token(
            username,
            role,
            teacher_id=username if role == "Teacher" else None,
            student_id=username if role == "Student" else None,
        )
        client.cookies.set(get_settings().auth_cookie, token)
        return client

    return factory


@pytest.fixture
def grant_permission() -> Iterator[Callable[[str, bool], None]]:
    """暫時調整教師開課權限，測試結束後還原"""
    original: dict[str, bool] = {}

    def set_permission(teacher_id: str, value: bool) -> None:
        with SessionLocal() as db:
            teacher = db.get_one(Teacher, teacher_id)
            original.setdefault(teacher_id, teacher.can_open_section)
            teacher.can_open_section = value
            db.commit()

    yield set_permission
    with SessionLocal() as db:
        for teacher_id, value in original.items():
            db.get_one(Teacher, teacher_id).can_open_section = value
        db.commit()
