"""

Middleware 主要在 HTTP Request 進入路由前，以及 Response 傳回用戶端前，
統一處理多個端點共用的橫切關注點，例如登入與權限檢查、請求限流、
錯誤回應轉換及安全標頭設定，避免每個 route 重複實作相同邏輯。

注意：本目錄中的檔案不一定都是 FastAPI / ASGI Middleware；
例如 require_auth 使用 Dependency Injection，rate_limit 則是由 route 主動呼叫的限流工具。

"""