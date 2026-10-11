"""認證測試（移植自原 Express 的 vitest 測試，並補上限流、密碼長度與修改密碼）"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.middleware.rate_limit import login_limiter, password_limiter
from app.models import Role, UserAccount
from app.services.auth_service import hash_password

PASSWORD = get_settings().seed_password
COOKIE = get_settings().auth_cookie


@pytest.fixture(scope="module", autouse=True)
def _require_seed_password() -> None:
    """本檔的測試需要以種子帳號實際登入；未設定密碼時整個模組跳過"""
    if not PASSWORD:
        pytest.skip("需要在 .env 設定 SEED_PASSWORD 才能測試登入")


def login(username: str) -> TestClient:
    """走正式登入流程，回傳已帶 cookie 的 client（TestClient 會自動保存回應的 cookie）"""
    client = TestClient(app)
    res = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return client


def test_login_sets_secure_cookie_without_exposing_token():
    """登入回傳使用者資訊，JWT 只放在 HttpOnly + SameSite 的 cookie 中"""
    res = TestClient(app).post("/api/auth/login", json={"username": "S001", "password": PASSWORD})
    assert res.status_code == 200
    assert res.json()["user"] == {
        "sub": res.json()["user"]["sub"],
        "username": "S001",
        "role": "Student",
        "name": "張飛",
        "teacher_id": None,
        "student_id": "S001",
    }
    assert "eyJ" not in res.text  # JWT 只存在 cookie 中，不出現在回應內容
    cookie = res.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie or "SameSite=Lax" in cookie


def test_wrong_password_and_unknown_user_look_the_same():
    """帳號不存在與密碼錯誤回傳相同訊息，避免帳號列舉"""
    client = TestClient(app)
    wrong_pw = client.post("/api/auth/login", json={"username": "S001", "password": "wrong-password"})
    no_user = client.post("/api/auth/login", json={"username": "nobody", "password": "wrong-password"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_overlong_password_is_rejected_not_crashing():
    """bcrypt 5 對超過 72 bytes 的輸入會拋例外；必須回 401 而非 500"""
    res = TestClient(app).post("/api/auth/login", json={"username": "S001", "password": "密" * 30})
    assert res.status_code == 401


def test_unauthenticated_and_tampered_token():
    """沒有 cookie、或 token 使用 alg=none 偽造時，一律 401"""
    client = TestClient(app)
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("access_token", "eyJhbGciOiJub25lIn0.e30.")  # alg=none
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_current_user():
    """/me 回傳 JWT 中的身分（教師帳號帶有 teacher_id）"""
    res = login("T001").get("/api/auth/me")
    assert res.json()["user"]["teacher_id"] == "T001"
    assert res.json()["user"]["role"] == "Teacher"


def test_logout_clears_cookie():
    """登出後 cookie 被清除，再呼叫 /me 回 401"""
    client = login("S001")
    res = client.post("/api/auth/logout")
    assert res.status_code == 204
    assert 'access_token=""' in res.headers["set-cookie"] or "Max-Age=0" in res.headers["set-cookie"]
    assert client.get("/api/auth/me").status_code == 401


def test_login_rate_limited():
    """用完登入次數後，即使密碼正確也回 429，並附 Retry-After 標頭"""
    login_limiter.reset()
    client = TestClient(app)
    for _ in range(login_limiter.limit):
        client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    # 第 limit + 1 次
    res = client.post("/api/auth/login", json={"username": "S001", "password": PASSWORD})
    assert res.status_code == 429
    assert "Retry-After" in res.headers


# ---------------------------------------------------------------------
# 修改密碼：使用暫時帳號，不改動種子帳號的密碼
# ---------------------------------------------------------------------

TEMP_USERNAME = "test_pw_user"
TEMP_PASSWORD = "Temp-Passw0rd"
NEW_PASSWORD = "New-Passw0rd!"


@pytest.fixture
def temp_account() -> Iterator[int]:
    """建立暫時的管理員帳號（沒有個人資料表，刪除時不牽涉其他表），測試結束後刪除"""
    with SessionLocal() as db:
        db.execute(delete(UserAccount).where(UserAccount.username == TEMP_USERNAME))
        account = UserAccount(username=TEMP_USERNAME, password_hash=hash_password(TEMP_PASSWORD), role=Role.Admin)
        db.add(account)
        db.commit()
        user_id = account.user_id
    try:
        yield user_id
    finally:
        with SessionLocal() as db:
            db.execute(delete(UserAccount).where(UserAccount.user_id == user_id))
            db.commit()


def login_as(username: str, password: str) -> TestClient:
    client = TestClient(app)
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return client


def test_change_own_password(temp_account):
    """修改自己的密碼：驗證目前密碼；成功後本裝置維持登入，舊的 token 與舊密碼都失效"""
    client = login_as(TEMP_USERNAME, TEMP_PASSWORD)
    old_token = client.cookies.get(COOKIE)

    # 目前密碼錯誤 → 400（不是 401，前端才不會把使用者登出），且登入狀態不受影響
    res = client.post("/api/auth/password", json={"current_password": "wrong", "new_password": NEW_PASSWORD})
    assert res.status_code == 400
    assert res.json()["detail"] == "目前的密碼不正確"
    assert client.get("/api/auth/me").status_code == 200

    res = client.post("/api/auth/password", json={"current_password": TEMP_PASSWORD, "new_password": TEMP_PASSWORD})
    assert res.status_code == 400
    assert res.json()["detail"] == "新密碼不可與目前的密碼相同"

    # 新密碼不符規則（少於 8 字元）→ 422
    res = client.post("/api/auth/password", json={"current_password": TEMP_PASSWORD, "new_password": "short"})
    assert res.status_code == 422

    res = client.post("/api/auth/password", json={"current_password": TEMP_PASSWORD, "new_password": NEW_PASSWORD})
    assert res.status_code == 204
    assert COOKIE in res.headers["set-cookie"]
    # 本裝置改用新 cookie，維持登入
    assert client.cookies.get(COOKIE) != old_token
    assert client.get("/api/auth/me").status_code == 200

    # 其他裝置上的舊 token 立即失效
    other_device = TestClient(app)
    other_device.cookies.set(COOKIE, old_token)
    res = other_device.get("/api/auth/me")
    assert res.status_code == 401
    assert res.json()["detail"] == "密碼已變更，請重新登入"

    # 舊密碼不能再登入，新密碼可以
    old = TestClient(app).post("/api/auth/login", json={"username": TEMP_USERNAME, "password": TEMP_PASSWORD})
    assert old.status_code == 401
    login_as(TEMP_USERNAME, NEW_PASSWORD)


def test_admin_reset_password_invalidates_sessions(temp_account, client_as):
    """管理員重設密碼後，該帳號既有的登入全部失效，新密碼可以登入"""
    user_client = login_as(TEMP_USERNAME, TEMP_PASSWORD)
    admin = client_as("admin", role="Admin")

    res = admin.patch(f"/api/admin/users/{temp_account}", json={"password": NEW_PASSWORD})
    assert res.status_code == 200, res.text

    assert user_client.get("/api/auth/me").status_code == 401
    login_as(TEMP_USERNAME, NEW_PASSWORD)


def test_admin_cannot_reset_own_password(client_as):
    """管理員不可用重設功能改自己的密碼（必須經由修改密碼驗證目前密碼）"""
    with SessionLocal() as db:
        admin_id = db.scalar(select(UserAccount.user_id).where(UserAccount.username == "admin"))
    res = client_as("admin", role="Admin").patch(f"/api/admin/users/{admin_id}", json={"password": NEW_PASSWORD})
    assert res.status_code == 400
    assert "修改密碼" in res.json()["detail"]


def test_change_password_rate_limited(temp_account):
    """以帳號為單位限流：用完次數後即使目前密碼正確也回 429"""
    client = login_as(TEMP_USERNAME, TEMP_PASSWORD)
    for _ in range(password_limiter.limit):
        client.post("/api/auth/password", json={"current_password": "wrong", "new_password": NEW_PASSWORD})
    res = client.post("/api/auth/password", json={"current_password": TEMP_PASSWORD, "new_password": NEW_PASSWORD})
    assert res.status_code == 429
    assert "Retry-After" in res.headers
