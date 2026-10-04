from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError

from app.routers import admin, auth, common, student, teacher

app = FastAPI(
    title="教務管理系統 API",
    description="認證、管理員、開課、選課（先搶先贏）、成績與歷年查詢。認證使用 httpOnly cookie 中的 JWT。",
    version="2.0.0",
    # Swagger UI 掛在 /api/docs，透過 Next.js 同源存取時會自動帶上登入 cookie
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(common.router)
app.include_router(teacher.router)
app.include_router(student.router)


# MySQL 錯誤碼 → 對使用者的說明（未列出的錯誤維持 500）
DB_ERRORS: dict[int, tuple[int, str]] = {
    1062: (status.HTTP_409_CONFLICT, "資料重複，違反唯一性約束"),
    1451: (status.HTTP_409_CONFLICT, "此資料仍被其他資料參照，無法刪除或修改"),
    1452: (status.HTTP_409_CONFLICT, "參照的資料不存在"),
    3819: (status.HTTP_422_UNPROCESSABLE_CONTENT, "資料不符合資料庫的檢查約束"),
}


@app.exception_handler(DBAPIError)
async def db_error_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    """資料庫約束是最後一道防線；違反時回傳與一般錯誤相同的 { detail } 格式"""
    code = exc.orig.args[0] if exc.orig is not None and exc.orig.args else None
    if code in DB_ERRORS:
        http_status, message = DB_ERRORS[code]
        return JSONResponse({"detail": message}, status_code=http_status)
    raise exc


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
