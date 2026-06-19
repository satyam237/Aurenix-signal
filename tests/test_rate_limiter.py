from __future__ import annotations

import time

from shared.rate_limiter import TokenBucketRateLimiter


def test_token_bucket_acquires_without_error() -> None:
    limiter = TokenBucketRateLimiter(requests_per_minute=60)
    start = time.monotonic()
    for _ in range(3):
        limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 2.0
