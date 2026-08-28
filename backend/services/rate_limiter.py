"""
rate_limiter.py — IP-based sliding window rate limiter.
"""
import asyncio
import time
from collections import deque
from backend.config import get_settings

class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Too many requests. Please wait {retry_after} seconds.")

class RateLimiter:
    def __init__(self):
        # Dictionary of ip -> deque of timestamps
        self._store: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, ip: str) -> None:
        settings = get_settings()
        limit = settings.rate_limit_requests
        window = settings.rate_limit_window_seconds
        now = time.monotonic()

        async with self._lock:
            if ip not in self._store:
                self._store[ip] = deque()

            timestamps = self._store[ip]

            # Remove stale timestamps
            while timestamps and now - timestamps[0] > window:
                timestamps.popleft()

            if len(timestamps) >= limit:
                # Calculate retry after
                oldest = timestamps[0]
                retry_after = int(window - (now - oldest))
                if retry_after <= 0:
                    retry_after = 1
                raise RateLimitExceeded(retry_after=retry_after)

            # Record the new request
            timestamps.append(now)

# Singleton
rate_limiter = RateLimiter()
