"""
簡易的登入限流（sliding window，存在記憶體中）。

限制：計數存在單一 process 的記憶體內；
若以多個 worker 或多台主機部署，每個 process 各自計數，需改用 Redis(是一個分散式資料庫) 等共享儲存。
"""

import threading
import time
from collections import defaultdict, deque

from app.errors import TooManyRequestsError
from fastapi import Request

# 定義「哪些連線來源可以被信任為本機反向代理」
# 127.0.0.1 是 IPv4 loopback、::1 是 IPv6 loopback、localhost 是本機主機名稱。
# 這份集合檢查的是「誰直接連到 FastAPI」，不是檢查 X-Forwarded-For 內的 IP 是否合法。
LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def client_ip(request: Request) -> str:
    """
    只信任本機反向代理（Next.js rewrites）帶來的 X-Forwarded-For；
    直接連線的用戶端無法偽造此 header 來繞過限流。

    這個函式的工作是「選擇哪個字串作為限流 key」，不是驗證合法連線或合法 IP：
    - 不會以 ipaddress 等工具檢查 IPv4／IPv6 格式。
    - 不會查 IP 白名單、黑名單或地理位置。
    - 不會因 IP 可疑而拒絕 Request；它只回傳一個字串交給 RateLimiter 計數。

    判斷流程：
    1. request.client.host 是直接和 FastAPI 建立連線的來源。
    2. 若直接來源是 LOOPBACK，代表請求可能經本機 Next.js 轉送，便取
       X-Forwarded-For 最左邊的值作為原始用戶端 IP。
    3. 若直接來源不是 LOOPBACK，忽略可能由外部用戶端自行填寫的 X-Forwarded-For，
       改用實際連線來源 host，避免直接連 FastAPI 時只靠更換 header 繞過限流。

    範例：
    - 經 Next.js：host="127.0.0.1"、X-Forwarded-For="203.0.113.10"
      → 回傳 "203.0.113.10"。
    - 直接連 FastAPI：host="198.51.100.20"、X-Forwarded-For="1.1.1.1"
      → 忽略 header，回傳 "198.51.100.20"。

    安全限制：只有在反向代理會覆寫或清除用戶端傳入的 X-Forwarded-For 時，
    代理提供的值才能視為可信。Next.js 16 會保留已存在的 X-Forwarded-For，
    因此目前實作仍可能讓經由 Next.js 的非瀏覽器用戶端偽造此值；這個記憶體限流器
    只能降低暴力嘗試的頻率，不應視為完整的安全邊界。正式部署時應由受信任的反向代理
    統一清理並重建 X-Forwarded-For，且不要把 FastAPI port 直接暴露到外網。
    """
    host = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if host in LOOPBACK and forwarded:
        return forwarded.split(",")[0].strip()
    return host


class RateLimiter:
    """
    每個 key（IP 或帳號）保留一個時間戳佇列，只計算最近 window_seconds 秒內的請求
    請求超過 limit 時丟出 TooManyRequestsError，並告訴使用者多久後才會空出名額。
    """
    def __init__(self, limit: int, window_seconds: float, message: str) -> None:
        self.limit = limit
        self.window = window_seconds
        self.message = message  # 超過上限時回傳給使用者的訊息
        # key → 最近的請求時間戳佇列（deque）：deque 兩端 pop/append O(1)，適合 sliding window
        # _hits 就是「同一個 key 的請求時間戳佇列」的集合，key 可以是用戶端 IP 或帳號
        # 例如：{"192.168.1.1": deque([1634567890.123, 1634567891.456]), "user123": deque([1634567892.789, 1634567893.012])}
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        # FastAPI 的同步路由在 thread pool 中執行，多個請求可能同時修改同一個佇列
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """記錄一次請求；超過上限時丟出 TooManyRequestsError（該次不計入）"""
        # monotonic 不受系統時間調整影響，適合計算時間間隔
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            # 移除已滑出時間窗的舊紀錄
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                # 等到最舊的一筆滑出時間窗，才會空出名額
                retry_after = int(self.window - (now - hits[0])) + 1
                raise TooManyRequestsError(self.message, retry_after)
            hits.append(now)

    def reset(self) -> None:
        """清空所有計數（測試用，避免前一個測試的登入次數影響下一個）"""
        with self._lock:
            self._hits.clear()


# 同一 IP 每 15 分鐘最多 20 次登入嘗試，降低暴力破解風險
login_limiter = RateLimiter(limit=20, window_seconds=15 * 60, message="登入嘗試次數過多，請稍後再試")
# 同一帳號每 15 分鐘最多 10 次修改密碼：避免取得登入狀態的人藉此暴力猜測目前的密碼
password_limiter = RateLimiter(limit=10, window_seconds=15 * 60, message="修改密碼嘗試次數過多，請稍後再試")
