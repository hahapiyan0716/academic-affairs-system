"""選課規則與併發控制測試"""

import threading

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import ACTIVE_ENROLLMENT, Enrollment, SemesterStatus
from app.services.enrollment import enroll


def test_enroll_then_withdraw(make_section, client_as):
    sid = make_section()
    s001 = client_as("S001")

    res = s001.post("/api/enrollments", json={"section_id": sid})
    assert res.status_code == 201, res.text
    assert res.json()["status"] == "Selected"

    # 重複加選同一班
    assert s001.post("/api/enrollments", json={"section_id": sid}).status_code == 409

    res = s001.delete(f"/api/enrollments/{sid}")
    assert res.status_code == 200
    assert res.json()["status"] == "Withdrawn"

    # 退選後可重新加選（沿用同一筆紀錄）
    assert s001.post("/api/enrollments", json={"section_id": sid}).status_code == 201


def test_full_section_rejected(make_section, client_as):
    sid = make_section(capacity=1)
    assert client_as("S001").post("/api/enrollments", json={"section_id": sid}).status_code == 201

    res = client_as("S003").post("/api/enrollments", json={"section_id": sid})
    assert res.status_code == 409
    assert "額滿" in res.json()["detail"]


def test_time_conflict_rejected(make_section, client_as):
    a = make_section(course_no="A0001", slots=[(2, 3, "O313"), (2, 4, "O313")])
    b = make_section(course_no="A0002", slots=[(2, 4, "L102")])
    s001 = client_as("S001")
    assert s001.post("/api/enrollments", json={"section_id": a}).status_code == 201

    res = s001.post("/api/enrollments", json={"section_id": b})
    assert res.status_code == 409
    assert "衝堂" in res.json()["detail"]


def test_same_course_twice_rejected(make_section, client_as):
    a = make_section(course_no="A0003", section_code="01", slots=[(3, 1, "O313")])
    b = make_section(course_no="A0003", section_code="02", slots=[(4, 1, "O313")])
    s001 = client_as("S001")
    assert s001.post("/api/enrollments", json={"section_id": a}).status_code == 201

    res = s001.post("/api/enrollments", json={"section_id": b})
    assert res.status_code == 409
    assert "同一門課" in res.json()["detail"]


def test_suspended_student_rejected(make_section, client_as):
    sid = make_section()
    # S002 孫尚香為休學狀態
    res = client_as("S002").post("/api/enrollments", json={"section_id": sid})
    assert res.status_code == 403


def test_semester_not_enrolling(semester, make_section, client_as):
    sid = make_section()
    semester(SemesterStatus.InProgress)
    res = client_as("S001").post("/api/enrollments", json={"section_id": sid})
    assert res.status_code == 409
    assert "不開放" in res.json()["detail"]


def test_browse_marks_conflict(make_section, client_as):
    a = make_section(course_no="A0001", slots=[(5, 1, "O313")])
    b = make_section(course_no="A0002", slots=[(5, 1, "L102")])
    s001 = client_as("S001")
    s001.post("/api/enrollments", json={"section_id": a})

    rows = {r["section_id"]: r for r in s001.get("/api/sections?semester_id=9991").json()}
    assert rows[a]["my_status"] == "Selected" and rows[a]["conflict"] is False
    assert rows[b]["conflict"] is True


def test_auth_required(make_section, client_as):
    from fastapi.testclient import TestClient

    from app.main import app

    assert TestClient(app).get("/api/sections").status_code == 401
    # 學生不可呼叫教師 API
    assert client_as("S001").get("/api/teacher/sections").status_code == 403


@pytest.mark.parametrize("round_", range(3))
def test_concurrent_enrollment_never_oversells(make_section, round_):
    """
    8 位學生同時搶 3 個名額：FOR UPDATE 鎖讓請求依序通過名額檢查，
    結果必須剛好 3 人成功、5 人收到「額滿」，資料庫中的有效選課數也必須是 3。
    """
    capacity = 3
    sid = make_section(capacity=capacity)
    students = ["S001", "S003", "S004", "S005", "S006", "S007", "S009", "S011"]
    barrier = threading.Barrier(len(students))
    results: dict[str, str] = {}

    def worker(student_id: str) -> None:
        with SessionLocal() as db:
            barrier.wait()  # 所有執行緒同時起跑，盡可能製造競爭
            try:
                enroll(db, student_id, sid)
                results[student_id] = "ok"
            except HTTPException as exc:
                results[student_id] = exc.detail

    threads = [threading.Thread(target=worker, args=(s,)) for s in students]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    succeeded = [s for s, r in results.items() if r == "ok"]
    assert len(succeeded) == capacity, results
    assert all(r == "此班級已額滿" for r in results.values() if r != "ok"), results

    with SessionLocal() as db:
        count = db.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.section_id == sid, Enrollment.status.in_(ACTIVE_ENROLLMENT))
        )
    assert count == capacity
