"""
health.py — Health check endpoint.

GET /health → probes fal.ai, Replicate, and Groq in parallel.
Returns per-service reachability + latency. Never exposes key values.
"""
import asyncio
import time
from fastapi import APIRouter

from backend.models.schemas import HealthResponse, ServiceHealth
from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


async def _probe_fal() -> ServiceHealth:
    """Lightweight fal.ai reachability check."""
    import httpx
    settings = get_settings()
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.head(
                "https://fal.ai",
                headers={"Authorization": f"Key {settings.fal_key}"},
            )
        latency = (time.monotonic() - start) * 1000
        # 401/403/422 = reachable (auth or validation issue, server is up)
        reachable = resp.status_code < 500
        return ServiceHealth(reachable=reachable, latency_ms=round(latency, 1))
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        return ServiceHealth(reachable=False, latency_ms=round(latency, 1), error=str(exc))


async def _probe_replicate() -> ServiceHealth:
    """Lightweight Replicate reachability check."""
    import httpx
    settings = get_settings()
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://api.replicate.com/v1/models/luma/dream-machine",
                headers={"Authorization": f"Bearer {settings.replicate_api_token}"},
            )
        latency = (time.monotonic() - start) * 1000
        reachable = resp.status_code < 500
        return ServiceHealth(reachable=reachable, latency_ms=round(latency, 1))
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        return ServiceHealth(reachable=False, latency_ms=round(latency, 1), error=str(exc))


async def _probe_groq() -> ServiceHealth:
    """Lightweight Groq reachability check."""
    import httpx
    settings = get_settings()
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            )
        latency = (time.monotonic() - start) * 1000
        reachable = resp.status_code < 500
        return ServiceHealth(reachable=reachable, latency_ms=round(latency, 1))
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        return ServiceHealth(reachable=False, latency_ms=round(latency, 1), error=str(exc))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Probe all three providers in parallel and report reachability."""
    fal_result, replicate_result, groq_result = await asyncio.gather(
        _probe_fal(),
        _probe_replicate(),
        _probe_groq(),
        return_exceptions=False,
    )

    services = {
        "fal_ai": fal_result,
        "replicate": replicate_result,
        "groq": groq_result,
    }

    all_ok = all(s.reachable for s in services.values())
    status = "ok" if all_ok else "degraded"

    logger.info(
        "health_check",
        status=status,
        fal_reachable=fal_result.reachable,
        replicate_reachable=replicate_result.reachable,
        groq_reachable=groq_result.reachable,
    )

    return HealthResponse(status=status, services=services)
