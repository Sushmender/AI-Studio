"""
conftest.py — Shared pytest configuration and fixtures for AI-Studio tests.

Provides:
  - asyncio_mode = "auto" via pytest.ini_options (set in pyproject.toml or pytest.ini)
  - Windows-safe event loop policy for asyncio tests
  - Reusable fixtures for isolated store/limiter instances
"""
import asyncio
import sys
import pytest


# ── Windows: prevent "no running event loop" errors in pytest-asyncio ────────

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def fresh_job_store():
    """Return a fresh, isolated JobStore instance (not the singleton)."""
    from backend.services.job_store import JobStore
    return JobStore()


@pytest.fixture
def fresh_rate_limiter():
    """Return a RateLimiter with test-friendly settings (5 req / 60 s)."""
    from backend.services.rate_limiter import RateLimiter
    return RateLimiter(max_requests=5, window_seconds=60)
