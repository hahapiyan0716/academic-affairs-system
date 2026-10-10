"""為每個回應加上基本的安全性標頭"""

from fastapi import FastAPI, Request


def register_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        # setdefault：路由若已自行設定同名標頭則不覆蓋
        # 禁止瀏覽器猜測 Content-Type，避免把 JSON 當成 HTML／JS 執行
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # 禁止被其他網頁以 iframe 嵌入，防止 Clickjacking
        response.headers.setdefault("X-Frame-Options", "DENY")
        # 不在 Referer 標頭洩漏來源網址
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response
