"""
錯誤 → HTTP 回應。所有錯誤一律回傳 { "detail": ... }（前端 lib/api.ts 依賴這個格式）。

- AppError（app/errors.py）：services 丟出的業務錯誤
- DBAPIError：資料庫約束是最後一道防線，依 MySQL 錯誤碼轉成 409／422
- 輸入驗證失敗由 FastAPI 自行回傳 422（detail 為錯誤清單）
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError

from app.errors import AppError, TooManyRequestsError

# MySQL 錯誤碼 → 對使用者的說明（未列出的錯誤維持 500）
DB_ERRORS: dict[int, tuple[int, str]] = {
    1062: (status.HTTP_409_CONFLICT, "資料重複，違反唯一性約束"),
    1451: (status.HTTP_409_CONFLICT, "此資料仍被其他資料參照，無法刪除或修改"),
    1452: (status.HTTP_409_CONFLICT, "參照的資料不存在"),
    3819: (status.HTTP_422_UNPROCESSABLE_CONTENT, "資料不符合資料庫的檢查約束"),
}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    headers = {"Retry-After": str(exc.retry_after)} if isinstance(exc, TooManyRequestsError) else None
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code, headers=headers)


async def db_error_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    code = exc.orig.args[0] if exc.orig is not None and exc.orig.args else None
    if code in DB_ERRORS:
        http_status, message = DB_ERRORS[code]
        return JSONResponse({"detail": message}, status_code=http_status)
    raise exc


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(DBAPIError, db_error_handler)  # type: ignore[arg-type]
