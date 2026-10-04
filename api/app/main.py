"""
進入點：建立 FastAPI 應用程式，依序掛上 middleware、錯誤處理與路由。
啟動：uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI

from app.middleware.error_handler import register_error_handlers
from app.middleware.security_headers import register_security_headers
from app.routes import admin, auth, common, student, teacher

app = FastAPI(
    title="教務管理系統 API",
    description="認證、管理員、開課、選課（先搶先贏）、成績與歷年查詢。認證使用 httpOnly cookie 中的 JWT。",
    version="2.0.0",
    # Swagger UI 掛在 /api/docs，透過 Next.js 同源存取時會自動帶上登入 cookie
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

register_security_headers(app)
register_error_handlers(app)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(common.router)
app.include_router(teacher.router)
app.include_router(student.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
