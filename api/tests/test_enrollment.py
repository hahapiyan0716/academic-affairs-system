"""選課規則與併發控制測試"""

import threading

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import ACTIVE_ENROLLMENT, Enrollment, SemesterStatus
from app.errors import AppError
from app.services.enrollment_service import enroll


def test_enroll_then_withdraw(make_section, client_as):
    """加選 → 重複加選被拒 → 退選 → 重新加選"""
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
    """名額已滿時加選失敗"""
    sid = make_section(capacity=1)
    assert client_as("S001").post("/api/enrollments", json={"section_id": sid}).status_code == 201

    res = client_as("S003").post("/api/enrollments", json={"section_id": sid})
    assert res.status_code == 409
    assert "額滿" in res.json()["detail"]


def test_time_conflict_rejected(make_section, client_as):
    """與已選課程有任一節重疊（星期二第 4 節）即視為衝堂"""
    a = make_section(course_no="A0001", slots=[(2, 3, "O313"), (2, 4, "O313")])
    b = make_section(course_no="A0002", slots=[(2, 4, "L102")])
    s001 = client_as("S001")
    assert s001.post("/api/enrollments", json={"section_id": a}).status_code == 201

    res = s001.post("/api/enrollments", json={"section_id": b})
    assert res.status_code == 409
    assert "衝堂" in res.json()["detail"]


def test_same_course_twice_rejected(make_section, client_as):
    """同一學期不可同時選同一門課的兩個班（時段不衝突也一樣）"""
    a = make_section(course_no="A0003", section_code="01", slots=[(3, 1, "O313")])
    b = make_section(course_no="A0003", section_code="02", slots=[(4, 1, "O313")])
    s001 = client_as("S001")
    assert s001.post("/api/enrollments", json={"section_id": a}).status_code == 201

    res = s001.post("/api/enrollments", json={"section_id": b})
    assert res.status_code == 409
    assert "同一門課" in res.json()["detail"]


def test_suspended_student_rejected(make_section, client_as):
    """非在學的學生不可選課"""
    sid = make_section()
    # S002 孫尚香為休學狀態
    res = client_as("S002").post("/api/enrollments", json={"section_id": sid})
    assert res.status_code == 403


def test_semester_not_enrolling(semester, make_section, client_as):
    """學期不在「選課中」時不可加選"""
    sid = make_section()
    semester(SemesterStatus.InProgress)
    res = client_as("S001").post("/api/enrollments", json={"section_id": sid})
    assert res.status_code == 409
    assert "不開放" in res.json()["detail"]


def test_browse_marks_conflict(make_section, client_as):
    """瀏覽班級時，已選的班不標衝堂，與它時段重疊的其他班標為衝堂"""
    a = make_section(course_no="A0001", slots=[(5, 1, "O313")])
    b = make_section(course_no="A0002", slots=[(5, 1, "L102")])
    s001 = client_as("S001")
    s001.post("/api/enrollments", json={"section_id": a})

    rows = {r["section_id"]: r for r in s001.get("/api/sections?semester_id=9991").json()}
    assert rows[a]["my_status"] == "Selected" and rows[a]["conflict"] is False
    assert rows[b]["conflict"] is True


def test_browse_filters_by_field(make_section, client_as):
    # 種子資料：A0007 演算法 ∈ 人工智慧、資料科學；A0005 統計學 ∈ 基礎知識
    ai = make_section(course_no="A0007", slots=[(1, 2, "O313")])
    basic = make_section(course_no="A0005", slots=[(1, 3, "O313")])
    s001 = client_as("S001")

    rows = {r["section_id"]: r for r in s001.get("/api/sections?semester_id=9991&field=人工智慧").json()}
    assert ai in rows and basic not in rows
    assert "人工智慧" in rows[ai]["field_names"].split("、")

    # 精確比對：領域名稱的一部分不會命中
    assert s001.get("/api/sections?semester_id=9991&field=人工").json() == []


def test_history_filters_by_field(make_section, client_as):
    ai = make_section(course_no="A0007", slots=[(1, 2, "O313")])
    basic = make_section(course_no="A0005", slots=[(1, 3, "O313")])

    rows = client_as("S001").get("/api/history/sections?field=人工智慧").json()
    ids = {r["section_id"] for r in rows}
    assert ai in ids and basic not in ids
    assert all("人工智慧" in r["field_names"].split("、") for r in rows)


def test_field_list_and_transcript_fields(client_as):
    s001 = client_as("S001")
    fields = s001.get("/api/fields").json()
    assert "人工智慧" in fields and len(fields) == len(set(fields))

    # S001 在 1132 學期有修課紀錄（種子資料）
    rows = [r for sem in s001.get("/api/me/transcript").json()["semesters"] for r in sem["rows"]]
    assert rows and all("field_names" in r for r in rows)


def test_auth_required(make_section, client_as):
    """未登入 401；角色不符 403"""
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

    # 每個執行緒使用自己的 Session（連線），直接呼叫 service，模擬多個同時進來的請求
    def worker(student_id: str) -> None:
        with SessionLocal() as db:
            barrier.wait()  # 所有執行緒同時起跑，盡可能製造競爭
            try:
                enroll(db, student_id, sid)
                results[student_id] = "ok"
            except AppError as exc:
                results[student_id] = exc.message

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
