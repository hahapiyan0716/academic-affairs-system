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
LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def client_ip(request: Request) -> str:
    """
    只信任本機反向代理（Next.js rewrites）帶來的 X-Forwarded-For；
    直接連線的用戶端無法偽造此 header 來繞過限流。
    """
    host = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if host in LOOPBACK and forwarded:
        return forwarded.split(",")[0].strip()
    return host


class RateLimiter:
    """每個 key（IP 或帳號）保留一個時間戳佇列，只計算最近 window_seconds 秒內的請求"""

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
