"""管理員 API 測試（移植自原 Express 的 vitest 測試；每個測試都會還原自己造成的變更）"""

import threading
from collections.abc import Iterator

import pytest
from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.errors import AppError
from app.models import Course, Semester, SemesterStatus, Student, Teacher, TeacherPermissionLog, UserAccount
from app.schemas.semester_schema import SemesterUpdateIn
from app.services.semester_service import update_semester


def test_non_admin_forbidden(client_as):
    """學生與教師呼叫管理員 API 一律 403"""
    for username, role in (("S001", "Student"), ("T001", "Teacher")):
        assert client_as(username, role=role).get("/api/admin/users").status_code == 403


def test_list_users_searches_student_and_teacher_ids(client_as):
    """帳號搜尋可用學號或教師代號命中，且不依賴登入帳號剛好與代號相同"""
    admin = client_as("admin", role="Admin")
    accounts = (
        {
            "role": "Teacher",
            "username": "search_teacher",
            "password": "Passw0rd!",
            "profile": {"teacher_id": "TZ999", "teacher_name": "搜尋教師", "dept_id": "D001"},
        },
        {
            "role": "Student",
            "username": "search_student",
            "password": "Passw0rd!",
            "profile": {
                "student_id": "SZ999",
                "student_name": "搜尋學生",
                "dept_id": "D001",
                "grade": 1,
                "class_code": "A",
            },
        },
    )
    try:
        for body in accounts:
            res = admin.post("/api/admin/users", json=body)
            assert res.status_code == 201, res.text

        teacher_res = admin.get("/api/admin/users", params={"q": "TZ999"})
        assert teacher_res.status_code == 200
        assert [user["username"] for user in teacher_res.json()] == ["search_teacher"]

        student_res = admin.get("/api/admin/users", params={"q": "SZ999"})
        assert student_res.status_code == 200
        assert [user["username"] for user in student_res.json()] == ["search_student"]
    finally:
        with SessionLocal() as db:
            db.execute(delete(Teacher).where(Teacher.teacher_id == "TZ999"))
            db.execute(delete(Student).where(Student.student_id == "SZ999"))
            db.execute(delete(UserAccount).where(UserAccount.username.in_(("search_teacher", "search_student"))))
            db.commit()


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


# 學期狀態測試專用的暫時學期（conftest 的 9991 給選課與開課測試使用）
EXTRA_SEMESTERS = ("9992", "9993")


def _delete_extra_semesters() -> None:
    with SessionLocal() as db:
        db.execute(delete(Semester).where(Semester.semester_id.in_(EXTRA_SEMESTERS)))
        db.commit()


@pytest.fixture
def enrolling_semester() -> Iterator[str]:
    """
    建立規劃中的暫時學期 9992、9993，回傳種子資料中唯一選課中的學期代碼（1151）。
    結束時刪除暫時學期，並直接寫資料庫把該學期還原為選課中（不經 API，不受學期規則影響）
    """
    _delete_extra_semesters()  # 上次測試若中途被中斷，可能留下殘餘資料
    with SessionLocal() as db:
        enrolling = db.scalars(select(Semester.semester_id).where(Semester.status == SemesterStatus.Enrolling)).all()
        assert len(enrolling) == 1, f"種子資料應剛好有一個選課中的學期：{enrolling}"
        db.add_all(Semester(semester_id=s, acad_year=int(s[:3]), term=int(s[3])) for s in EXTRA_SEMESTERS)
        db.commit()
    try:
        yield enrolling[0]
    finally:
        _delete_extra_semesters()
        with SessionLocal() as db:
            db.get_one(Semester, enrolling[0]).status = SemesterStatus.Enrolling
            db.commit()


def test_second_enrolling_semester_rejected(client_as, enrolling_semester):
    """已有學期在選課中時，不可再把另一個學期改為選課中，且狀態不會被寫入"""
    res = client_as("admin", role="Admin").patch("/api/admin/semesters/9992", json={"status": "Enrolling"})
    assert res.status_code == 409
    assert res.json()["detail"] == f"已有其他學期（{enrolling_semester}）在選課中，請先調整該學期的狀態"
    with SessionLocal() as db:
        assert db.get_one(Semester, "9992").status == SemesterStatus.Planning


def test_enrolling_semester_can_be_set_again(client_as, enrolling_semester):
    """本來就在選課中的學期再設一次選課中，不算與其他學期衝突"""
    admin = client_as("admin", role="Admin")
    res = admin.patch(f"/api/admin/semesters/{enrolling_semester}", json={"status": "Enrolling"})
    assert res.status_code == 200


def test_enrolling_allowed_after_closing_other(client_as, enrolling_semester):
    """先把原本選課中的學期改為上課中，另一個學期才能開放選課"""
    admin = client_as("admin", role="Admin")
    assert admin.patch(f"/api/admin/semesters/{enrolling_semester}", json={"status": "InProgress"}).status_code == 200
    res = admin.patch("/api/admin/semesters/9992", json={"status": "Enrolling"})
    assert res.status_code == 200
    assert res.json()["status"] == "Enrolling"


@pytest.mark.parametrize("round_", range(3))
def test_concurrent_enrolling_only_one_succeeds(enrolling_semester, round_):
    """
    沒有學期在選課中時，兩個請求同時把不同學期改為選課中：
    學期列的 FOR UPDATE 鎖讓兩者依序檢查，結果必須剛好一個成功、一個收到 409 的訊息
    """
    with SessionLocal() as db:
        db.get_one(Semester, enrolling_semester).status = SemesterStatus.InProgress
        db.commit()

    barrier = threading.Barrier(len(EXTRA_SEMESTERS))
    results: dict[str, str] = {}

    # 每個執行緒使用自己的 Session（連線），直接呼叫 service，模擬同時進來的兩個請求
    def worker(semester_id: str) -> None:
        with SessionLocal() as db:
            barrier.wait()
            try:
                update_semester(db, semester_id, SemesterUpdateIn(status="Enrolling"))
                results[semester_id] = "ok"
            except AppError as exc:
                results[semester_id] = exc.message

    threads = [threading.Thread(target=worker, args=(s,)) for s in EXTRA_SEMESTERS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert list(results.values()).count("ok") == 1, results
    with SessionLocal() as db:
        count = db.scalar(
            select(func.count()).select_from(Semester).where(Semester.status == SemesterStatus.Enrolling)
        )
    assert count == 1


@pytest.mark.parametrize("path", ["/api/admin/stats", "/api/admin/semesters", "/api/admin/courses", "/api/admin/departments"])
def test_admin_read_endpoints(client_as, path):
    """唯讀 API 的冒煙測試：確認能正常回應"""
    assert client_as("admin", role="Admin").get(path).status_code == 200
