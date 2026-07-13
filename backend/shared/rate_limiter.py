from __future__ import annotations

import threading
import time


class TokenBucketRateLimiter:
    """Simple token-bucket rate limiter (requests per minute)."""

    def __init__(self, requests_per_minute: int) -> None:
        self._capacity = max(1, requests_per_minute)
        self._tokens = float(self._capacity)
        self._refill_rate = self._capacity / 60.0
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
            self._last_refill = now

            if self._tokens < 1:
                wait_seconds = (1 - self._tokens) / self._refill_rate
                time.sleep(wait_seconds)
                self._tokens = 0
            else:
                self._tokens -= 1
