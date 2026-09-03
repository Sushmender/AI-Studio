"""
health.py — Health check endpoint.

GET /health → probes fal.ai, Replicate, and Groq in parallel.
Returns per-service reachability + latency. Never exposes key values.

Results are cached for 30 seconds to avoid hammering provider endpoints
on every poll — especially important since the frontend HUD might call
this on every render.
"""
import asyncio
import time
from fastapi import APIRouter

from backend.models.schemas import HealthResponse, ServiceHealth
from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["health"])

# ── 30-second in-process cache ────────────────────────────────────────────────
_CACHE_TTL = 30.0   # seconds
_health_cache: dict = {}   # keys: "result" (HealthResponse), "ts" (float)


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
                "https://api.replicate.com/v1/models/luma/ray-flash-2-720p",
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


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    response_description="Per-provider reachability status and latency",
)
async def health_check():
    """
    Probe all three AI providers in parallel and report reachability.

    - **fal.ai** — HEAD `https://fal.ai` with API key
    - **Replicate** — GET model metadata for `luma/ray-flash-2-720p`
    - **Groq** — GET `/v1/models` with API key

    Results are **cached for 30 seconds** — safe to call frequently from the
    frontend HUD without hammering provider endpoints.

    `status` is `"ok"` if all services are reachable, `"degraded"` otherwise.
    """
    now = time.monotonic()

    # Return cached result if still fresh
    if _health_cache and (now - _health_cache["ts"]) < _CACHE_TTL:
        logger.info("health_check_cached", age_s=round(now - _health_cache["ts"], 1))
        return _health_cache["result"]

    # Run probes in parallel
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

    result = HealthResponse(status=status, services=services)

    # Store in cache
    _health_cache["result"] = result
    _health_cache["ts"] = now

    logger.info(
        "health_check",
        status=status,
        fal_reachable=fal_result.reachable,
        replicate_reachable=replicate_result.reachable,
        groq_reachable=groq_result.reachable,
    )

    return result
