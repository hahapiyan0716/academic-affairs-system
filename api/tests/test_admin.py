"""管理員 API 測試（移植自原 Express 的 vitest 測試；每個測試都會還原自己造成的變更）"""

import pytest
from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.models import Course, Student, Teacher, TeacherPermissionLog, UserAccount


def test_non_admin_forbidden(client_as):
    """學生與教師呼叫管理員 API 一律 403"""
    for username, role in (("S001", "Student"), ("T001", "Teacher")):
        assert client_as(username, role=role).get("/api/admin/users").status_code == 403


def test_permission_toggle_writes_audit_log(client_as):
    """切換開課權限時寫入一筆稽核紀錄，教師列表的 latest_log 也隨之更新"""
    admin = client_as("admin", role="Admin")
    with SessionLocal() as db:
        before = db.get_one(Teacher, "T005").can_open_section
        # 記下目前最大的 log_id，之後只檢查與清除本測試新增的紀錄
        max_log = db.scalar(select(func.max(TeacherPermissionLog.log_id))) or 0

    try:
        res = admin.patch("/api/admin/teachers/T005/permission", json={"can_open_section": not before})
        assert res.status_code == 200
        assert res.json()["can_open_section"] is (not before)
        with SessionLocal() as db:
            logs = db.scalars(select(TeacherPermissionLog).where(TeacherPermissionLog.log_id > max_log)).all()
        assert [(log.teacher_id, log.granted) for log in logs] == [("T005", not before)]

        latest = next(t for t in admin.get("/api/admin/teachers").json() if t["teacher_id"] == "T005")
        assert latest["latest_log"]["granted"] is (not before)
        assert latest["latest_log"]["admin"]["username"] == "admin"
    finally:
        with SessionLocal() as db:
            db.get_one(Teacher, "T005").can_open_section = before
            db.execute(delete(TeacherPermissionLog).where(TeacherPermissionLog.log_id > max_log))
            db.commit()


def test_validation_error(client_as):
    """請求內容型別錯誤時由 FastAPI 回 422"""
    res = client_as("admin", role="Admin").patch(
        "/api/admin/teachers/T005/permission", json={"can_open_section": "maybe"}
    )
    assert res.status_code == 422


def test_cannot_deactivate_self(client_as):
    """管理員不可停用自己的帳號"""
    admin = client_as("admin", role="Admin")
    with SessionLocal() as db:
        admin_id = db.scalar(select(UserAccount.user_id).where(UserAccount.username == "admin"))
    assert admin.patch(f"/api/admin/users/{admin_id}", json={"is_active": False}).status_code == 400


def test_deactivated_account_rejected_immediately(client_as):
    """帳號被停用後，尚未過期的 JWT 也立即失效（401）；重新啟用後恢復"""
    s005 = client_as("S005")
    assert s005.get("/api/auth/me").status_code == 200

    admin = client_as("admin", role="Admin")
    with SessionLocal() as db:
        user_id = db.scalar(select(UserAccount.user_id).where(UserAccount.username == "S005"))
    try:
        assert admin.patch(f"/api/admin/users/{user_id}", json={"is_active": False}).status_code == 200
        for path in ("/api/auth/me", "/api/me/timetable", "/api/sections"):
            res = s005.get(path)
            assert res.status_code == 401, path
            assert "停用" in res.json()["detail"]
    finally:
        # 重新啟用，不留下改動
        assert admin.patch(f"/api/admin/users/{user_id}", json={"is_active": True}).status_code == 200
    assert s005.get("/api/auth/me").status_code == 200


def test_duplicate_course_conflict(client_as):
    """課號重複時由資料庫的主鍵約束擋下，轉成 409"""
    res = client_as("admin", role="Admin").post(
        "/api/admin/courses",
        json={"course_no": "A0001", "course_name": "重複", "course_type": "Elective", "credit": 2},
    )
    assert res.status_code == 409


def test_create_student_account_and_login(client_as):
    """建立學生帳號（帳號 + 個人資料同一交易），並以新帳號登入"""
    from fastapi.testclient import TestClient

    from app.main import app

    admin = client_as("admin", role="Admin")
    body = {
        "role": "Student",
        "username": "test_s999",
        "password": "Passw0rd!",
        "profile": {"student_id": "S999", "student_name": "測試生", "dept_id": "D001", "grade": 1, "class_code": "A"},
    }
    try:
        res = admin.post("/api/admin/users", json=body)
        assert res.status_code == 201, res.text
        assert res.json()["student"]["student_id"] == "S999"

        # 重複帳號 → 409，且不會留下半套資料
        assert admin.post("/api/admin/users", json=body).status_code == 409

        login = TestClient(app).post("/api/auth/login", json={"username": "test_s999", "password": "Passw0rd!"})
        assert login.status_code == 200
        assert login.json()["user"]["student_id"] == "S999"
    finally:
        with SessionLocal() as db:
            db.execute(delete(Student).where(Student.student_id == "S999"))
            db.execute(delete(UserAccount).where(UserAccount.username == "test_s999"))
            db.commit()


def test_update_course_fields_keeps_existing(client_as):
    """領域整批更新時，保留的領域不可因「先刪後增」觸發主鍵重複"""
    admin = client_as("admin", role="Admin")
    with SessionLocal() as db:
        original = [f.field_name for f in db.get_one(Course, "A0002").fields]
    try:
        res = admin.patch("/api/admin/courses/A0002", json={"fields": [*original, "測試領域"]})
        assert res.status_code == 200, res.text
        assert sorted(res.json()["fields"]) == sorted([*original, "測試領域"])
    finally:
        assert admin.patch("/api/admin/courses/A0002", json={"fields": original}).status_code == 200


@pytest.mark.parametrize("path", ["/api/admin/stats", "/api/admin/semesters", "/api/admin/courses", "/api/admin/departments"])
def test_admin_read_endpoints(client_as, path):
    """唯讀 API 的冒煙測試：確認能正常回應"""
    assert client_as("admin", role="Admin").get(path).status_code == 200
