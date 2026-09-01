"""
test_unit.py — Unit tests for AI-Studio backend components.

Coverage:
  - JobStore: create, update, get, concurrent access
  - RateLimiter: sliding window enforcement, reset after window
  - AsyncRetry: NonRetryable raises immediately, Retryable retries N times,
                retry_count bound to contextvars
"""
import asyncio
import time
import pytest

# ─────────────────────────────────────────────────────────────────────────────
# JobStore
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_job_store_create_and_get():
    from backend.services.job_store import JobStore
    from backend.models.schemas import JobRecord, GenerationMode, JobStatus

    store = JobStore()
    record = JobRecord(mode=GenerationMode.image, raw_prompt="test prompt", provider="fal.ai", model="flux/dev")
    await store.create_job(record)

    job = await store.get_job(record.job_id)
    assert job is not None
    assert job.job_id == record.job_id
    assert job.status == JobStatus.queued
    assert job.raw_prompt == "test prompt"


@pytest.mark.asyncio
async def test_job_store_update():
    from backend.services.job_store import JobStore
    from backend.models.schemas import JobRecord, GenerationMode, JobStatus

    store = JobStore()
    record = JobRecord(mode=GenerationMode.image, raw_prompt="update test", provider="fal.ai", model="flux/dev")
    await store.create_job(record)

    await store.update_job(record.job_id, status=JobStatus.generating)
    job = await store.get_job(record.job_id)
    assert job.status == JobStatus.generating

    await store.update_job(record.job_id, status=JobStatus.done, result_url="https://example.com/img.png", latency_ms=2500.0)
    job = await store.get_job(record.job_id)
    assert job.status == JobStatus.done
    assert job.result_url == "https://example.com/img.png"
    assert job.latency_ms == 2500.0


@pytest.mark.asyncio
async def test_job_store_get_missing():
    from backend.services.job_store import JobStore

    store = JobStore()
    result = await store.get_job("nonexistent-job-id")
    assert result is None


@pytest.mark.asyncio
async def test_job_store_concurrent_writes():
    """Multiple concurrent updates to the same job_id should not corrupt data."""
    from backend.services.job_store import JobStore
    from backend.models.schemas import JobRecord, GenerationMode, JobStatus

    store = JobStore()
    record = JobRecord(mode=GenerationMode.video, raw_prompt="concurrent test", provider="replicate", model="luma")
    await store.create_job(record)

    async def update_status(s: JobStatus):
        await store.update_job(record.job_id, status=s)

    # Fire 10 concurrent updates
    await asyncio.gather(*[update_status(JobStatus.generating) for _ in range(10)])
    job = await store.get_job(record.job_id)
    assert job is not None  # no crash, data accessible


# ─────────────────────────────────────────────────────────────────────────────
# RateLimiter
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limiter_allows_requests_under_limit():
    from backend.services.rate_limiter import RateLimiter

    limiter = RateLimiter(max_requests=5, window_seconds=60)
    for i in range(5):
        await limiter.check("192.168.1.1")  # should not raise


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit():
    from backend.services.rate_limiter import RateLimiter, RateLimitExceeded

    limiter = RateLimiter(max_requests=5, window_seconds=60)
    for _ in range(5):
        await limiter.check("10.0.0.1")

    with pytest.raises(RateLimitExceeded):
        await limiter.check("10.0.0.1")


@pytest.mark.asyncio
async def test_rate_limiter_different_ips_independent():
    from backend.services.rate_limiter import RateLimiter

    limiter = RateLimiter(max_requests=2, window_seconds=60)
    await limiter.check("1.2.3.4")
    await limiter.check("1.2.3.4")
    # Different IP should still be allowed
    await limiter.check("5.6.7.8")


@pytest.mark.asyncio
async def test_rate_limiter_window_reset():
    """Requests should be allowed again after the sliding window expires."""
    from backend.services.rate_limiter import RateLimiter

    limiter = RateLimiter(max_requests=2, window_seconds=1)
    await limiter.check("192.168.0.1")
    await limiter.check("192.168.0.1")

    # Window has not expired yet — 3rd request should fail
    from backend.services.rate_limiter import RateLimitExceeded
    with pytest.raises(RateLimitExceeded):
        await limiter.check("192.168.0.1")

    # Wait for window to slide past
    await asyncio.sleep(1.1)
    # Now should succeed
    await limiter.check("192.168.0.1")


# ─────────────────────────────────────────────────────────────────────────────
# AsyncRetry decorator
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_succeeds_first_attempt():
    from backend.utils.retry import async_retry

    call_count = 0

    @async_retry(max_attempts=3, backoff_base=0.01)
    async def always_succeeds():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await always_succeeds()
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_non_retryable_raises_immediately():
    from backend.utils.retry import async_retry, NonRetryableError

    call_count = 0

    @async_retry(max_attempts=3, backoff_base=0.01)
    async def raises_non_retryable():
        nonlocal call_count
        call_count += 1
        raise NonRetryableError("auth failed")

    with pytest.raises(NonRetryableError):
        await raises_non_retryable()

    # Should have only been called once — no retries on NonRetryableError
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_retryable_exhausts_attempts():
    from backend.utils.retry import async_retry, RetryableError

    call_count = 0

    @async_retry(max_attempts=3, backoff_base=0.01)
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise RetryableError("transient error")

    with pytest.raises(RetryableError):
        await always_fails()

    assert call_count == 3  # tried 3 times


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    from backend.utils.retry import async_retry, RetryableError

    call_count = 0

    @async_retry(max_attempts=3, backoff_base=0.01)
    async def fails_once():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RetryableError("first attempt fails")
        return "recovered"

    result = await fails_once()
    assert result == "recovered"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_binds_retry_count_contextvar():
    """After successful call, retry_count contextvar should be 0 (no retries needed)."""
    import structlog
    from backend.utils.retry import async_retry

    @async_retry(max_attempts=2, backoff_base=0.01)
    async def succeed():
        return 42

    structlog.contextvars.clear_contextvars()
    await succeed()
    ctx = structlog.contextvars.get_contextvars()
    assert ctx.get("retry_count") == 0


@pytest.mark.asyncio
async def test_retry_binds_retry_count_after_retries():
    """After 2 retries (3 total attempts), retry_count contextvar should be 2."""
    import structlog
    from backend.utils.retry import async_retry, RetryableError

    call_count = 0

    @async_retry(max_attempts=3, backoff_base=0.01)
    async def fail_twice():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RetryableError("transient")
        return "ok"

    structlog.contextvars.clear_contextvars()
    result = await fail_twice()
    assert result == "ok"
    ctx = structlog.contextvars.get_contextvars()
    assert ctx.get("retry_count") == 2
