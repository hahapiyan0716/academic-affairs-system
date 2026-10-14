"""
在 API 文件上標示「這支 API 可能回傳哪些錯誤狀態碼」。用法：在 router 或路由加上 responses=errors(404, 409)。

顯示在哪裡：只出現在 Swagger 文件（http://localhost:3000/api/docs），展開某支 API 後，
最下方 Responses 區塊會列出每個狀態碼、下方 DESCRIPTIONS 的說明，以及錯誤格式 ErrorOut（{"detail": "..."}）。
這是給開發者看的，使用者在系統畫面上看不到。

不影響實際行為：就算拿掉 errors(...)，API 回傳的狀態碼與錯誤訊息也完全一樣。實際的錯誤是另一條路徑：
  service 丟出 app/errors.py 的業務錯誤（例如 ConflictError("此班級已額滿")）
  → middleware/error_handler.py 轉成 HTTP 409 與 {"detail": "此班級已額滿"}
  → 前端 web/lib/api.ts 取出 detail 丟出 ApiError → 頁面以 toast 或錯誤區塊顯示給使用者
因此 service 新增或修改會丟出的錯誤時，要記得同步更新對應路由的 errors(...)，文件才不會和實際行為不一致。

422（輸入驗證失敗）由 FastAPI 自動列出，這裡不重複：路由只要有任何參數就會出現，
需登入的路由都有 cookie 參數 access_token，所以幾乎每支 API 都有 422。
"""

from typing import Any

from app.schemas.base import ErrorOut

DESCRIPTIONS = {
    400: "請求不符合業務規則（例如目前密碼錯誤、不可停用自己的帳號）",
    401: "尚未登入、登入已失效，或帳號已停用",
    403: "角色不符或沒有權限",
    404: "找不到指定的資料",
    409: "與現有資料衝突（例如資料重複、額滿、衝堂、學期狀態不允許此操作）",
    429: "嘗試次數過多，請稍後再試（回應帶有 Retry-After 標頭）",
}


def errors(*codes: int) -> dict[int | str, dict[str, Any]]:
    """產生 responses 參數：每個狀態碼對應錯誤格式 ErrorOut 與說明"""
    return {code: {"model": ErrorOut, "description": DESCRIPTIONS[code]} for code in codes}
