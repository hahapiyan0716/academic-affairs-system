"""
認證與授權檢查（FastAPI 依賴）。

FastAPI 以「依賴（Depends）」實作每支 API 的前置檢查，作用等同 Express 的 route middleware：
在路由參數宣告 AdminUser／TeacherUser／StudentUser，就會先驗證 cookie 中的 JWT、帳號狀態與角色。

這不是透過 @app.middleware("http") 或 app.add_middleware(...) 註冊的全域 Middleware，因此不會套用到每一支 API
（本專案的全域中介層是 security_headers.py：每個請求一律經過，用來加安全標頭）。
只有明確宣告 AnyUser／AdminUser／TeacherUser／StudentUser，或在 router 的 dependencies 中
加入這裡的依賴函式之端點，收到請求時才會執行認證。公開端點（例如登入）不會經過這些檢查。
"""

from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import ForbiddenError, UnauthorizedError
from app.services import auth_service
from app.session import CurrentUser, Role, decode_token


def get_current_user(
    db: Annotated[Session, Depends(get_db)],        # Depends(get_db) 會在每個請求中產生新的 Session，並在請求結束時自動關閉
    access_token: Annotated[str | None, Cookie()] = None,   # Cookie() 會自動從請求的 cookie 中取出 access_token，若沒有則傳入 None
) -> CurrentUser:
    """
    從 cookie 取出 JWT 並還原登入者；參數名稱 access_token 即 cookie 名稱。
    JWT 驗證通過後再查一次帳號狀態：停用帳號、變更過密碼的舊登入都必須立即失效，不能等 JWT 過期。
    同一個請求內 FastAPI 會快取依賴結果，這裡的 db 與路由拿到的是同一個 Session。

    受保護端點收到請求時，FastAPI 會先解析這個依賴所需的參數，再依序執行：
    1. Cookie() 依參數名稱讀取 access_token cookie。
    2. 沒有 access_token 時拋出 UnauthorizedError，路由函式不會執行。
    3. decode_token() 驗證 JWT 並還原 CurrentUser。
    4. ensure_session_valid() 查資料庫，確認帳號仍啟用且 token_version 仍有效。
    5. 全部通過後回傳 CurrentUser，FastAPI 再將它注入路由的 user 參數。

    這裡只負責「身分認證」與登入狀態，不負責驗證 request body、query parameter、
    path parameter 的業務格式；那些格式由路由型別宣告與 Pydantic schema 另外驗證。
    所有必要的參數解析與依賴檢查完成前，FastAPI 不會呼叫路由函式本體。
    """
    if not access_token:
        raise UnauthorizedError("尚未登入")
    user = decode_token(access_token)
    auth_service.ensure_session_valid(db, user)
    return user


def require_role(*roles: Role):
    """產生「登入且角色屬於 roles 之一」的依賴函式"""

    # require_role("Teacher") 會先建立並回傳 checker；真正收到 API 請求時，
    # FastAPI 才會因 Depends(checker) 執行 checker，不是每次匯入都直接檢查使用者。

    def checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        # checker 本身又依賴 get_current_user，因此一定會先完成 JWT 與帳號狀態檢查，
        # 才檢查角色。角色不符時拋出 403，路由函式本體不會執行。
        if user.role not in roles:
            raise ForbiddenError("權限不足")
        return user

    return checker


# 路由參數的型別別名：AnyUser 只要求登入，其餘另外限定角色
# Annotated[CurrentUser, Depends(...)] 會在路由中自動注入 user 物件，並在函式內使用
#
# Annotated 是 typing 提供的「型別 + 額外資訊」容器，基本格式為：
#     Annotated[基本型別, 額外資訊]
# 以 Annotated[CurrentUser, Depends(get_current_user)] 為例：
#   - CurrentUser：此參數最後會拿到的 Python 型別，供 IDE、型別檢查器與 FastAPI 參考。
#   - Depends(get_current_user)：給 FastAPI 讀取的 metadata，表示值不是由用戶端直接傳入，
#     而是要先執行 get_current_user()，再將其回傳值注入路由參數。
#
# Annotated 本身不會執行函式，也不會驗證 JWT；實際執行依賴的是 FastAPI，
# 實際認證的是 get_current_user／require_role。建立下列別名只是避免每個路由重複寫完整型別：
#
#     # 使用別名
#     def me(user: TeacherUser): ...
#
#     # 與上面相同，但直接展開寫法
#     def me(user: Annotated[CurrentUser, Depends(require_role("Teacher"))]): ...
#
# 每次受保護的 API 請求會依照下列順序處理：
#     請求進入
#       → FastAPI 看到 Depends(...)
#       → get_current_user 驗證 cookie、JWT 與帳號狀態
#       → 角色型別再由 require_role 檢查角色
#       → 成功後把 CurrentUser 注入 user
#       → 最後才執行路由函式本體
# 任一步驟拋出例外時，FastAPI 會直接產生錯誤回應，不會繼續執行路由函式。
#
AnyUser = Annotated[CurrentUser, Depends(get_current_user)]
AdminUser = Annotated[CurrentUser, Depends(require_role("Admin"))]
TeacherUser = Annotated[CurrentUser, Depends(require_role("Teacher"))]
StudentUser = Annotated[CurrentUser, Depends(require_role("Student"))]


def teacher_id_of(user: CurrentUser) -> str:
    """取出教師代碼；Teacher 角色的帳號理論上都有，缺少時表示帳號資料異常"""
    if not user.teacher_id:
        raise ForbiddenError("此帳號未連結教師資料")
    return user.teacher_id


def student_id_of(user: CurrentUser) -> str:
    """取出學號；Student 角色的帳號理論上都有，缺少時表示帳號資料異常"""
    if not user.student_id:
        raise ForbiddenError("此帳號未連結學生資料")
    return user.student_id


# -----------------------------------------------------------------------------
# 實際檢查範例
# -----------------------------------------------------------------------------
#
# 範例一：教師查詢自己的資料
#
#     # app/routes/teacher.py
#     @router.get("/me")
#     def me(user: TeacherUser, db: DB):
#         return teacher_service.get_teacher(db, teacher_id_of(user))
#
# 假設用戶端送出 GET /api/teacher/me，FastAPI 的處理方式如下：
#   1. FastAPI 讀到 user: TeacherUser；TeacherUser 展開後是：
#          Annotated[CurrentUser, Depends(require_role("Teacher"))]
#   2. require_role("Teacher") 在模組載入時已產生 checker；此時 FastAPI 執行該 checker。
#   3. checker 的 user 又宣告 Depends(get_current_user)，所以先執行 get_current_user。
#   4. get_current_user 的 Cookie() 從 Request Cookie 讀取名為 access_token 的值：
#        - 沒有 cookie：拋出 UnauthorizedError("尚未登入")，回傳 401，me() 不會執行。
#        - 有 cookie：交給 decode_token() 驗證簽章、有效期限並解析成 CurrentUser。
#        - JWT 無效或過期：認證失敗並回傳 401，me() 不會執行。
#   5. JWT 有效後，ensure_session_valid() 以資料庫再次確認帳號仍啟用，並確認
#      token_version 沒有因修改密碼等原因失效；不符合時回傳 401，me() 不會執行。
#   6. get_current_user 回傳 CurrentUser 後，checker 比對 user.role 是否為 "Teacher"：
#        - 不是 Teacher：拋出 ForbiddenError("權限不足")，回傳 403，me() 不會執行。
#        - 是 Teacher：checker 回傳同一個 CurrentUser，FastAPI 將它注入 me() 的 user。
#   7. 所有依賴皆成功後才呼叫 me()。函式內的 teacher_id_of(user) 會再確認該教師帳號
#      有 teacher_id；若帳號資料異常、沒有連結教師資料，則在這裡回傳 403。
#
# 範例二：登入權限檢查與 request body 格式檢查是兩套機制
#
#     def create_section(user: TeacherUser, db: DB, body: SectionCreate): ...
#
#   - user: TeacherUser 由本檔案負責，檢查 cookie、JWT、帳號狀態與 Teacher 角色。
#   - body: SectionCreate 由 FastAPI／Pydantic 負責，檢查 JSON 欄位、資料型別與限制條件。
#   - 兩項都通過後，FastAPI 才會執行 create_section() 的函式本體。
#   - 因此 Annotated 並不是「檢查所有輸入格式」；它只把型別與 Depends metadata 綁在一起，
#     實際檢查項目仍由 Depends 指定的函式，以及個別 Pydantic schema 決定。
