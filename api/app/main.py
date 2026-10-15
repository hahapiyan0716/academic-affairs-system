"""
進入點：建立 FastAPI 應用程式，依序掛上 middleware、錯誤處理與路由。
啟動：uvicorn app.main:app --reload --port 8000 (這邊指定 port 8000，Next.js 會在 3000 轉送到這個 port)
"""

from fastapi import FastAPI, status

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
    redoc_url=None,     # redoc 是另一個 OpenAPI 文件 UI，這裡不需要
)

register_security_headers(app)      
register_error_handlers(app)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(common.router)
app.include_router(teacher.router)
app.include_router(student.router)


@app.get("/health", tags=["health"], status_code=status.HTTP_200_OK)
def health():
    """健康檢查：只確認 process 存活，不查資料庫"""
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# API 錯誤從產生到顯示的完整路徑（以「學生加選時班級已額滿」為例）
# -----------------------------------------------------------------------------
#
# 1. web/app/student/page.tsx
#    使用者按下加選，頁面透過 web/lib/api.ts 的 api() 發出 POST /api/enrollments。
#
# 2. web/next.config.ts
#    Next.js rewrites 將瀏覽器對 localhost:3000/api/* 的同源請求轉送到 FastAPI :8000。
#    若網路或 Next.js 在這一步失敗，請求不會進入下面的 FastAPI 錯誤處理流程。
#
# 3. 本檔案 main.py
#    register_security_headers(app) 掛上全域 HTTP 中介層；register_error_handlers(app)
#    註冊 AppError 與 DBAPIError 的例外處理器；include_router() 讓 FastAPI 能比對路由。
#
# 4. middleware/security_headers.py
#    中介層先以 call_next(request) 把請求交給下一層；取得成功或錯誤 Response 後，
#    再統一加入安全標頭。因此 401、404、409、422 等回應也會有安全標頭。
#
# 5. routes/student.py + FastAPI Dependency Injection
#    FastAPI 比對到 enroll()。在呼叫函式本體前，會先完成：
#      - DB = Depends(get_db)：建立本次 Request 使用的 SQLAlchemy Session。
#      - StudentUser：require_auth.py 驗證 cookie、JWT、帳號狀態與 Student 角色。
#      - EnrollIn：Pydantic 驗證 JSON 是否有整數 section_id；格式錯誤由 FastAPI 自動回 422。
#
# 6. services/enrollment_service.py + repositories/
#    route 呼叫 enrollment_service.enroll()；service 透過 repository 查詢學籍、班級、
#    選課期間、重複修課、衝堂與名額。額滿時執行：
#        raise ConflictError("此班級已額滿")
#    raise 會立刻中斷目前流程，所以後面的 db.commit() 不會執行。
#
# 7. errors.py + middleware/error_handler.py
#    ConflictError 是 AppError 子類別，status_code = 409。已在本檔案註冊的
#    app_error_handler() 會將它轉成：
#        HTTP 409
#        {"detail": "此班級已額滿"}
#    TooManyRequestsError 會另外附上 Retry-After；已知 DBAPIError 則依 MySQL 錯誤碼
#    轉成 409／422。未預期錯誤維持 500，避免把內部訊息洩漏給用戶端。
#
# 8. db.py 的 get_db()
#    Request 結束後關閉 Session；若錯誤發生在 commit 前，尚未提交的 Transaction
#    會自動 rollback，不會留下只完成一半的資料。
#
# 9. Response 回程
#    error_handler 建立 Response
#      → security_headers.py 加安全標頭
#      → Next.js rewrites 傳回瀏覽器
#      → web/lib/api.ts 讀取 detail 並丟出 ApiError(409, "此班級已額滿")
#      → student/page.tsx 的 onError 以 toast 顯示訊息。
#
# 不同錯誤來源：
# - 前端表單檢查：頁面直接顯示，不會發 Request。
# - Pydantic 格式錯誤：FastAPI 自動回 422，不經自訂 app_error_handler()。
# - 認證／角色錯誤：require_auth.py 丟出 AppError，轉成 401／403。
# - 業務規則錯誤：services/ 丟出 AppError，轉成 400／403／404／409。
# - 限流：rate_limit.py 丟出 TooManyRequestsError，轉成 429 + Retry-After。
# - 資料庫約束：error_handler.py 將已知 DBAPIError 轉成 409／422。
# - 網路／反向代理錯誤：請求可能未到 FastAPI，不經後端 error_handler。
#
# routes/error_responses.py 的 errors(...) 只產生 Swagger 文件中的錯誤說明，
# 不會捕捉或產生實際錯誤；真正的執行期路徑是 errors.py → error_handler.py。
