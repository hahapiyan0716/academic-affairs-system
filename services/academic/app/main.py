from fastapi import FastAPI

from app.routers import common, student, teacher

app = FastAPI(
    title="教務系統 — 教務核心服務",
    description="開課、選課（先搶先贏）、成績、歷年查詢。認證由 auth-admin 服務簽發的 JWT Cookie 負責。",
    version="1.0.0",
    # Swagger UI 掛在 /api/docs，透過 Next.js 同源存取時會自動帶上登入 cookie
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

app.include_router(common.router)
app.include_router(teacher.router)
app.include_router(student.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "academic"}
