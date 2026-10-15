"""
為每個回應加上基本的安全性標頭（全域 HTTP 中介層）。
中介層（middleware）包在整個應用程式外面：每一個 HTTP 請求都會先經過它，回應送出前也再經過它一次。
套用範圍是「全部」，包含成功回應、錯誤回應（401、404、422……）、/api/docs 與 /health，
所以適合做與個別路由無關、而且一個都不能漏的事，例如加安全標頭。

    瀏覽器的請求
      → security_headers（call_next 之前：這裡沒有要做的事）
      → call_next(request)：交給下一層 → 路由比對 → 依賴（require_auth）→ 路由函式 → service
      → security_headers（call_next 之後：在回應加上安全標頭）
      → 回應送回瀏覽器

與 require_auth.py 的差別：require_auth 是「依賴（Depends）」，只有宣告了 AnyUser／AdminUser 等參數
（或 router 的 dependencies）的路由才會執行；登入、登出等公開端點不會經過。中介層則不分路由一律執行。

包成 register_security_headers(app) 由 main.py 呼叫：@app.middleware 需要 app 物件，
由 main.py 傳入就不必在這裡 import main.py，避免循環 import（error_handler.py 也是同樣做法）。
"""

from fastapi import FastAPI, Request


def register_security_headers(app: FastAPI) -> None:
    # 註冊全域 HTTP 中介層："http" 表示處理 HTTP 請求（ASGI 另有 websocket 等類型，此裝飾器只支援 "http"）
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        # call_next 把請求交給下一層並等待回應；寫在它之前的程式在處理請求前執行，之後的程式可修改回應
        response = await call_next(request)
        # 以下在「取得回應之後、送回瀏覽器之前」執行（真正送回是最後的 return response）。
        # 這三個標頭只會加在 FastAPI 產生的回應（/api/* 與 /api/docs）；
        # /student 等頁面由 Next.js 產生，不經過這裡。
        #
        # setdefault：標頭還不存在時才設定；路由若已自行設定同名標頭（例如 SAMEORIGIN）則保留原值，
        # 這裡提供的是預設值。若改用 response.headers[...] = ... 則會強制覆蓋。

        # 禁止 MIME sniffing：瀏覽器必須照 Content-Type 處理，不可自行猜測類型。
        # 避免含使用者輸入的 JSON 被猜成 HTML 渲染而執行其中的腳本（XSS），
        # 也讓其他網站無法以 <script src="/api/..."> 把 JSON 當成 JavaScript 執行
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # 禁止被任何網頁（含同網站）以 iframe 嵌入，防止點擊劫持（Clickjacking）：
        # 攻擊者把本站疊在透明 iframe 下，誘使已登入的使用者點到「退選」等按鈕。SAMEORIGIN 則只允許同網站嵌入
        response.headers.setdefault("X-Frame-Options", "DENY")
        # 完全不送 Referer 標頭，避免網址中的資訊（例如 ?q=搜尋的姓名）洩漏給外部網站；
        # 例如 /api/docs 從外部 CDN 載入 Swagger UI 時，CDN 不會得知文件網址
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

"""
【什麼是標頭】
每個 HTTP 回應都分成「標頭（headers）」與「內容（body）」。標頭是寫在前面、給瀏覽器看的說明
（內容是什麼類型、有多長、能不能快取……），使用者在畫面上看不到；內容才是真正的 JSON 或 HTML。
可以想成包裹：標頭是外箱上的標籤，內容是箱子裡的東西。

每個回應「原本就有」標頭，安全標頭只是額外再貼上的幾張標籤。以 GET /api/semesters 為例（未登入，401）：
    content-length: 25                  ┐ 原本就有：FastAPI 自動產生，描述內容
    content-type: application/json     ┘
    x-content-type-options: nosniff     ┐
    x-frame-options: DENY               ├ 安全標頭：這個中介層加上去的
    referrer-policy: no-referrer        ┘
安全標頭不會自動出現，沒有人加就不會有。

【三個安全標頭】（詳細說明見下方各行註解）
    標頭                              意思                                防止的攻擊
    X-Content-Type-Options: nosniff   照 Content-Type 處理，不准猜類型    MIME sniffing 造成的 XSS（JSON 被當成 HTML／JS 執行）
    X-Frame-Options: DENY             不准被任何網頁用 iframe 嵌入        點擊劫持（Clickjacking）
    Referrer-Policy: no-referrer      不送 Referer（來源網址）            網址中的資訊洩漏給外部網站
"""