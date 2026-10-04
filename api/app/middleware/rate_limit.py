"""
簡易的登入限流（sliding window，存在記憶體中）。

限制：計數存在單一 process 的記憶體內；若以多個 worker 或多台主機部署，
每個 process 各自計數，需改用 Redis 等共享儲存。
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.errors import TooManyRequestsError

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
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = int(self.window - (now - hits[0])) + 1
                raise TooManyRequestsError("登入嘗試次數過多，請稍後再試", retry_after)
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# 同一 IP 每 15 分鐘最多 20 次登入嘗試，降低暴力破解風險
login_limiter = RateLimiter(limit=20, window_seconds=15 * 60)
