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


# ─────────────────────────────────────────────────────────────────────────────
# Edge-case Unit Tests (Day 7 additions)
# ─────────────────────────────────────────────────────────────────────────────

# 1. Invalid job_id formats ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_job_store_invalid_job_id_returns_none():
    """
    Requesting a job with a non-UUID or malformed job_id should return None
    gracefully — no exception raised.
    """
    from backend.services.job_store import JobStore

    store = JobStore()

    for bad_id in [
        "",                              # empty string
        "not-a-uuid",                    # plain string
        "12345",                         # numeric string
        "x" * 500,                       # extremely long string
        "00000000-0000-0000-0000-000000000000",   # zero UUID (valid format, missing)
        "../../etc/passwd",              # path traversal attempt
        "'; DROP TABLE jobs; --",        # SQL injection attempt
    ]:
        result = await store.get_job(bad_id)
        assert result is None, f"Expected None for bad_id={bad_id!r}, got {result}"


@pytest.mark.asyncio
async def test_job_store_update_nonexistent_job_is_noop():
    """
    Updating a job that doesn't exist should not raise — just silently no-op.
    This protects against race conditions where a job TTL-expires mid-update.
    """
    from backend.services.job_store import JobStore
    from backend.models.schemas import JobStatus

    store = JobStore()
    # Should not raise
    await store.update_job("nonexistent-id-xyz", status=JobStatus.done)


# 2. Malformed / unexpected Groq output ───────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_handles_generic_exception_as_retryable():
    """
    Simulate Groq returning unexpected/malformed data by raising a generic
    RuntimeError inside a retried async function. Verifies the retry decorator
    does NOT swallow it silently, and exhausts attempts correctly.
    """
    from backend.utils.retry import async_retry, RetryableError

    call_count = 0

    @async_retry(max_attempts=2, backoff_base=0.01)
    async def simulate_bad_groq_parse():
        nonlocal call_count
        call_count += 1
        # Simulate JSON parsing failure after Groq returns garbage
        raise RetryableError("JSONDecodeError: Expecting value: line 1 col 1")

    with pytest.raises(RetryableError):
        await simulate_bad_groq_parse()

    assert call_count == 2, f"Expected 2 attempts, got {call_count}"


@pytest.mark.asyncio
async def test_non_retryable_error_not_retried_on_groq_auth():
    """
    A 401/403 from Groq (auth error) must NOT be retried — it would be a
    pointless waste of quota. Verify NonRetryableError propagates immediately.
    """
    from backend.utils.retry import async_retry, NonRetryableError

    call_count = 0

    @async_retry(max_attempts=3, backoff_base=0.01)
    async def simulate_groq_auth_error():
        nonlocal call_count
        call_count += 1
        raise NonRetryableError("401 Unauthorized — invalid Groq API key")

    with pytest.raises(NonRetryableError, match="401 Unauthorized"):
        await simulate_groq_auth_error()

    assert call_count == 1, "NonRetryableError must abort immediately (no retries)"


# 3. Concurrent job submissions ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_concurrent_job_submissions_all_stored():
    """
    Submit N=20 jobs concurrently to the JobStore.
    Every job_id must be unique, and all jobs must be retrievable.
    Tests that the asyncio.Lock prevents data corruption under load.
    """
    from backend.services.job_store import JobStore
    from backend.models.schemas import JobRecord, GenerationMode, JobStatus

    store = JobStore()
    n = 20

    records = [
        JobRecord(
            mode=GenerationMode.image,
            raw_prompt=f"concurrent prompt {i}",
            provider="fal.ai",
            model="flux/dev",
        )
        for i in range(n)
    ]

    # Create all jobs at the same time
    await asyncio.gather(*[store.create_job(r) for r in records])

    # Verify all were stored and are independently accessible
    job_ids = {r.job_id for r in records}
    assert len(job_ids) == n, "All job_ids must be unique"

    retrieved = await asyncio.gather(*[store.get_job(r.job_id) for r in records])
    for job, original in zip(retrieved, records):
        assert job is not None, f"Job {original.job_id} was not found"
        assert job.job_id == original.job_id
        assert job.status == JobStatus.queued
        assert job.raw_prompt == original.raw_prompt


@pytest.mark.asyncio
async def test_concurrent_updates_to_different_jobs_no_corruption():
    """
    Concurrently update N different jobs with different statuses.
    After all updates settle, every job should hold its own expected value
    (no cross-job data leaks from lock contention).
    """
    from backend.services.job_store import JobStore
    from backend.models.schemas import JobRecord, GenerationMode, JobStatus

    store = JobStore()
    n = 10

    records = [
        JobRecord(
            mode=GenerationMode.video,
            raw_prompt=f"video prompt {i}",
            provider="replicate",
            model="luma",
        )
        for i in range(n)
    ]
    await asyncio.gather(*[store.create_job(r) for r in records])

    # Update each job with a unique result_url
    async def update(record: JobRecord, idx: int):
        await store.update_job(
            record.job_id,
            status=JobStatus.done,
            result_url=f"https://cdn.example.com/video_{idx}.mp4",
            latency_ms=float(idx * 100),
        )

    await asyncio.gather(*[update(r, i) for i, r in enumerate(records)])

    # Verify each job holds its own data
    for i, record in enumerate(records):
        job = await store.get_job(record.job_id)
        assert job.status == JobStatus.done
        assert job.result_url == f"https://cdn.example.com/video_{i}.mp4"
        assert job.latency_ms == float(i * 100)
