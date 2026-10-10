"""教師開課權限、教室／教師衝堂、登分與稽核紀錄測試"""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import ScoreChangeLog, SemesterStatus


def _payload(**overrides):
    """開課請求的預設內容（測試學期 9991、星期一第 2 節、教室 I1-018），可用關鍵字參數覆寫個別欄位"""
    body = {
        "course_no": "A0004",
        "semester_id": "9991",
        "section_code": "01",
        "capacity": 30,
        "slots": [{"weekday": 1, "period": 2, "room_code": "I1-018"}],
    }
    return body | overrides


def test_teacher_without_permission_cannot_open(semester, client_as, grant_permission):
    """沒有開課權限的教師開課 → 403"""
    grant_permission("T002", False)
    res = client_as("T002", role="Teacher").post("/api/teacher/sections", json=_payload())
    assert res.status_code == 403


def test_permission_revoked_takes_effect_immediately(semester, client_as, grant_permission):
    """權限不放在 JWT 內，收回後即使 token 未過期也立即失效"""
    grant_permission("T001", True)
    t001 = client_as("T001", role="Teacher")
    assert t001.post("/api/teacher/sections", json=_payload()).status_code == 201

    grant_permission("T001", False)
    res = t001.post("/api/teacher/sections", json=_payload(section_code="02", slots=[
        {"weekday": 2, "period": 2, "room_code": "I1-018"}]))
    assert res.status_code == 403


def test_room_conflict_rejected(semester, client_as, grant_permission):
    """不同教師在同學期、同時段借用同一間教室 → 409"""
    grant_permission("T001", True)
    grant_permission("T003", True)
    assert client_as("T001", role="Teacher").post("/api/teacher/sections", json=_payload()).status_code == 201

    res = client_as("T003", role="Teacher").post(
        "/api/teacher/sections", json=_payload(course_no="A0005")
    )
    assert res.status_code == 409
    assert "教室" in res.json()["detail"]


def test_teacher_time_conflict_rejected(semester, client_as, grant_permission):
    """同一位教師在同時段開兩個班 → 409"""
    grant_permission("T001", True)
    t001 = client_as("T001", role="Teacher")
    assert t001.post("/api/teacher/sections", json=_payload()).status_code == 201

    # 同一位教師、同時段、不同教室
    res = t001.post(
        "/api/teacher/sections",
        json=_payload(course_no="A0005", slots=[{"weekday": 1, "period": 2, "room_code": "O313"}]),
    )
    assert res.status_code == 409
    assert "教師衝堂" in res.json()["detail"]


def test_closed_semester_cannot_open(semester, client_as, grant_permission):
    """已結束的學期不可開課"""
    grant_permission("T001", True)
    semester(SemesterStatus.Finished)
    res = client_as("T001", role="Teacher").post("/api/teacher/sections", json=_payload())
    assert res.status_code == 409


def test_grades_and_audit_log(semester, make_section, client_as):
    """登分的學期狀態限制、成績稽核紀錄、輸入驗證與授課教師檢查"""
    sid = make_section(teacher_id="T001")
    assert client_as("S001").post("/api/enrollments", json={"section_id": sid}).status_code == 201
    t001 = client_as("T001", role="Teacher")

    # 選課中不可登分
    res = t001.put(f"/api/teacher/sections/{sid}/grades", json={"grades": [{"student_id": "S001", "score": 80}]})
    assert res.status_code == 409

    semester(SemesterStatus.InProgress)
    res = t001.put(f"/api/teacher/sections/{sid}/grades", json={"grades": [{"student_id": "S001", "score": 80}]})
    assert res.status_code == 200 and res.json()["updated"] == 1

    res = t001.put(f"/api/teacher/sections/{sid}/grades", json={"grades": [{"student_id": "S001", "score": 85.5}]})
    assert res.json()["updated"] == 1

    # 成績未變動時不寫入稽核紀錄
    res = t001.put(f"/api/teacher/sections/{sid}/grades", json={"grades": [{"student_id": "S001", "score": 85.5}]})
    assert res.json() == {"updated": 0, "unchanged": 1}

    # 未修課的學生、超出範圍的成績
    res = t001.put(f"/api/teacher/sections/{sid}/grades", json={"grades": [{"student_id": "S003", "score": 60}]})
    assert res.status_code == 404
    res = t001.put(f"/api/teacher/sections/{sid}/grades", json={"grades": [{"student_id": "S001", "score": 101}]})
    assert res.status_code == 422

    with SessionLocal() as db:
        logs = db.scalars(
            select(ScoreChangeLog).where(ScoreChangeLog.section_id == sid).order_by(ScoreChangeLog.log_id)
        ).all()
    assert [(log.old_score, log.new_score) for log in logs] == [(None, 80), (80, 85.5)]

    # 其他教師看不到這個班
    assert client_as("T002", role="Teacher").get(f"/api/teacher/sections/{sid}/roster").status_code == 404
