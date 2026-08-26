"""
retry.py — Async exponential-backoff retry decorator.

Rules:
  - Retries on: asyncio.TimeoutError, httpx.TimeoutException, 5xx HTTP errors
  - Does NOT retry on: 4xx errors (validation / auth issues)
  - Max attempts: configurable (default 2)
  - Backoff: base ** attempt seconds between retries
"""
import asyncio
import functools
import time
from typing import Callable, Type

import httpx

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class RetryableError(Exception):
    """Wrap a transient error to signal the retry decorator."""
    pass


class NonRetryableError(Exception):
    """Wrap a non-retryable error (4xx, validation) to skip retries."""
    pass


def _is_retryable(exc: BaseException) -> bool:
    """Return True if this exception warrants a retry."""
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return True
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


def async_retry(
    max_attempts: int = 2,
    backoff_base: float = 1.5,
    retryable_exceptions: tuple[Type[BaseException], ...] = (
        asyncio.TimeoutError,
        TimeoutError,
        httpx.TimeoutException,
        httpx.HTTPStatusError,
        RetryableError,
    ),
) -> Callable:
    """
    Decorator factory. Wraps an async function with retry + backoff.

    Usage:
        @async_retry(max_attempts=2, backoff_base=1.5)
        async def my_fn(): ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except NonRetryableError:
                    raise
                except retryable_exceptions as exc:
                    if not _is_retryable(exc):
                        raise  # e.g. 4xx HTTPStatusError — propagate immediately
                    last_exc = exc
                    if attempt < max_attempts:
                        wait = backoff_base ** (attempt - 1)
                        logger.warning(
                            "retry_scheduled",
                            attempt=attempt,
                            max_attempts=max_attempts,
                            wait_seconds=round(wait, 2),
                            error=str(exc),
                            func=func.__name__,
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.error(
                            "retry_exhausted",
                            attempt=attempt,
                            max_attempts=max_attempts,
                            error=str(exc),
                            func=func.__name__,
                        )
                except Exception as exc:
                    # Unexpected — propagate immediately, don't retry
                    raise
            raise last_exc  # type: ignore[misc]

        return wrapper
    return decorator
