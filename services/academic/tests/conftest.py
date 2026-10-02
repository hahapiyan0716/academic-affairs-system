"""
測試共用設定。

測試直接連 .env 中的資料庫，但所有資料都建立在專用的測試學期 '9991'（999 學年第 1 學期），
每個測試結束後只刪除該學期底下的資料，不影響種子資料。
"""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
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
    _cleanup()
    with SessionLocal() as db:
        db.add(Semester(semester_id=TEST_SEMESTER, acad_year=999, term=1, status=SemesterStatus.Enrolling))
        db.commit()

    def set_status(status: SemesterStatus) -> None:
        with SessionLocal() as db:
            db.get_one(Semester, TEST_SEMESTER).status = status
            db.commit()

    yield set_status
    _cleanup()


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
    with SessionLocal() as db:
        return db.execute(text("SELECT user_id FROM UserAccount WHERE username = :u"), {"u": username}).scalar_one()


def make_token(username: str, role: str, *, teacher_id: str | None = None, student_id: str | None = None) -> str:
    """模擬 Express 簽發的 JWT（相同 secret、issuer、演算法）"""
    settings = get_settings()
    payload = {
        "sub": str(_user_id(username)),
        "username": username,
        "role": role,
        "name": username,
        "teacher_id": teacher_id,
        "student_id": student_id,
        "iss": settings.jwt_issuer,
        "exp": datetime.now(UTC) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


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
