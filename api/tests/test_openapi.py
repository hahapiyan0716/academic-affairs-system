"""API 文件（OpenAPI）測試：確認路由標示的成功與錯誤狀態碼，以及錯誤回應的格式"""

import pytest

from app.main import app


@pytest.fixture(scope="module")
def paths() -> dict:
    return app.openapi()["paths"]


@pytest.mark.parametrize(
    ("path", "method", "expected"),
    [
        # router 層的 401／403 會併入每支路由。
        # 422 由 FastAPI 自動加上：路由只要有任何參數就會列出，需登入的路由都有 cookie 參數 access_token
        ("/api/enrollments", "post", {"201", "401", "403", "404", "409", "422"}),
        ("/api/enrollments/{section_id}", "delete", {"200", "401", "403", "404", "409", "422"}),
        ("/api/admin/semesters/{semester_id}", "patch", {"200", "401", "403", "404", "409", "422"}),
        ("/api/teacher/sections", "post", {"201", "401", "403", "404", "409", "422"}),
        ("/api/auth/login", "post", {"200", "401", "403", "429", "422"}),
        ("/api/auth/logout", "post", {"204"}),  # 不需登入、沒有任何參數，因此沒有 422
        ("/api/semesters", "get", {"200", "401", "422"}),
    ],
)
def test_documented_status_codes(paths, path, method, expected):
    """文件列出的狀態碼與實際可能的回應一致"""
    assert set(paths[path][method]["responses"]) == expected


def test_error_response_uses_error_schema(paths):
    """錯誤回應的格式為 ErrorOut（{"detail": "..."}），422 則維持 FastAPI 的驗證錯誤格式"""
    responses = paths["/api/enrollments"]["post"]["responses"]
    assert responses["409"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorOut")
    assert responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/HTTPValidationError")
