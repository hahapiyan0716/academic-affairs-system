"""認證測試（移植自原 Express 的 vitest 測試，並補上限流與密碼長度）"""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.middleware.rate_limit import login_limiter

PASSWORD = get_settings().seed_password


@pytest.fixture(scope="module", autouse=True)
def _require_seed_password() -> None:
    if not PASSWORD:
        pytest.skip("需要在 .env 設定 SEED_PASSWORD 才能測試登入")


def login(username: str) -> TestClient:
    client = TestClient(app)
    res = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return client


def test_login_sets_secure_cookie_without_exposing_token():
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
    client = TestClient(app)
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("access_token", "eyJhbGciOiJub25lIn0.e30.")  # alg=none
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_current_user():
    res = login("T001").get("/api/auth/me")
    assert res.json()["user"]["teacher_id"] == "T001"
    assert res.json()["user"]["role"] == "Teacher"


def test_logout_clears_cookie():
    client = login("S001")
    res = client.post("/api/auth/logout")
    assert res.status_code == 204
    assert 'access_token=""' in res.headers["set-cookie"] or "Max-Age=0" in res.headers["set-cookie"]
    assert client.get("/api/auth/me").status_code == 401


def test_login_rate_limited():
    login_limiter.reset()
    client = TestClient(app)
    for _ in range(login_limiter.limit):
        client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    res = client.post("/api/auth/login", json={"username": "S001", "password": PASSWORD})
    assert res.status_code == 429
    assert "Retry-After" in res.headers
