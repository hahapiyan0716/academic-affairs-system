"""
API 文件（/api/docs）用的錯誤狀態碼說明：在 router 或路由加上 responses=errors(404, 409)。

只影響 Swagger 文件，不改變實際行為：錯誤由 services 丟出 app/errors.py 的業務錯誤，
再由 middleware/error_handler.py 轉成 HTTP 回應。
422（輸入驗證失敗）由 FastAPI 自動列出，這裡不重複。
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
