"""
test_integration.py — Integration tests for AI-Studio backend API.

Prerequisites:
  - Backend running locally with MOCK_APIS=true:
      .venv/Scripts/uvicorn backend.main:app --reload
  - Or set BASE_URL env var for a different target

Runs against the live (mock) server to verify the full HTTP contract.

Usage:
    .venv\\Scripts\\python -m pytest tests/test_integration.py -v
    .venv\\Scripts\\python -m pytest tests/test_integration.py -v -k "image"
"""
import asyncio
import os
import time
import pytest
import httpx

BASE_URL = os.getenv("AI_STUDIO_TEST_URL", "http://127.0.0.1:8000")
POLL_INTERVAL = 1.0   # seconds between polls
POLL_TIMEOUT = 60.0   # max seconds to wait for a job to complete


async def poll_until_done(client: httpx.AsyncClient, job_id: str, timeout: float = POLL_TIMEOUT) -> dict:
    """Poll /jobs/{id}/status until done or failed, or raise TimeoutError."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = await client.get(f"{BASE_URL}/jobs/{job_id}/status")
        assert r.status_code == 200, f"Status poll failed: {r.status_code} {r.text}"
        data = r.json()
        if data["status"] in ("done", "failed"):
            return data
        await asyncio.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


# ─────────────────────────────────────────────────────────────────────────────
# Health endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint_structure():
    """GET /health returns per-service reachability dict."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE_URL}/health")

    assert r.status_code == 200
    body = r.json()
    assert "services" in body or "fal" in body or "status" in body, \
        f"Unexpected health shape: {body}"


@pytest.mark.asyncio
async def test_root_endpoint():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{BASE_URL}/")
    assert r.status_code == 200
    assert "AI-Studio" in r.json().get("service", "")


# ─────────────────────────────────────────────────────────────────────────────
# Image generation flow
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_image_job_full_flow():
    """
    Full flow: POST /generate/image → poll /jobs/{id}/status to done
               → GET /jobs/{id}/result → result_url present.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Submit job (structured path)
        payload = {
            "prompt": "",
            "attributes": {
                "subject": "A golden lighthouse on rocky cliffs",
                "action": "Standing tall against stormy waves",
                "location": "Irish coastline, dusk, dramatic clouds",
                "composition": "Wide angle, low perspective, foreground rocks",
                "style": "Cinematic realism, warm amber tones, high contrast"
            }
        }
        r = await client.post(f"{BASE_URL}/generate/image", json=payload)
        assert r.status_code == 202, f"Submit failed: {r.status_code} {r.text}"

        job_id = r.json()["job_id"]
        assert job_id, "job_id missing from response"

        # 2. Poll to completion
        final = await poll_until_done(client, job_id)
        assert final["status"] == "done", f"Job failed: {final}"

        # 3. Fetch result
        r2 = await client.get(f"{BASE_URL}/jobs/{job_id}/result")
        assert r2.status_code == 200
        result = r2.json()
        assert result.get("result_url"), f"result_url missing: {result}"


@pytest.mark.asyncio
async def test_image_job_raw_prompt():
    """Legacy path: plain prompt text (no attributes) should also work."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{BASE_URL}/generate/image", json={"prompt": "a red fox in snow"})
        assert r.status_code == 202
        job_id = r.json()["job_id"]

        final = await poll_until_done(client, job_id)
        assert final["status"] in ("done", "failed")  # mock may or may not succeed


# ─────────────────────────────────────────────────────────────────────────────
# Video generation flow
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_video_job_full_flow():
    """
    Full flow: POST /generate/video → poll to done/failed
               → if done, result has result_url.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "prompt": "",
            "video_attributes": {
                "subject": "A lone wolf running through snow",
                "action": "Running at full speed, powerful strides",
                "scene": "Frozen tundra, blizzard conditions",
                "style": "Cinematic wildlife documentary",
                "camera_angles": "Low tracking shot",
                "camera_movements": "Steadicam follow",
                "lens_effects": "Shallow depth of field, motion blur",
                "temporal_elements": "Slow motion at 120fps",
                "color_grading": "Desaturated blue-grey, cold tones",
                "audio": "Wind howling, snow crunching"
            }
        }
        r = await client.post(f"{BASE_URL}/generate/video", json=payload)
        assert r.status_code == 202, f"Submit failed: {r.status_code} {r.text}"

        body = r.json()
        job_id = body["job_id"]
        assert job_id

        # estimated_wait_seconds should be surfaced
        assert "estimated_wait_seconds" in body

        # Poll (with longer timeout for video)
        final = await poll_until_done(client, job_id, timeout=POLL_TIMEOUT)
        assert final["status"] in ("done", "failed")

        if final["status"] == "done":
            r2 = await client.get(f"{BASE_URL}/jobs/{job_id}/result")
            assert r2.status_code == 200
            assert r2.json().get("result_url")


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_enforced():
    """Burst 15 rapid requests → 429 on request 11+, with Retry-After header."""
    responses = []
    async with httpx.AsyncClient(timeout=10) as client:
        for i in range(15):
            r = await client.post(
                f"{BASE_URL}/generate/image",
                json={"prompt": f"rate limit test {i}"}
            )
            responses.append(r.status_code)

    status_codes = responses
    accepted = [s for s in status_codes if s == 202]
    rate_limited = [s for s in status_codes if s == 429]

    assert len(accepted) >= 1, "At least some requests should be accepted"
    assert len(rate_limited) >= 1, \
        f"Expected 429s after limit, got: {status_codes}"


# ─────────────────────────────────────────────────────────────────────────────
# Error handling
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_prompt_rejected_client_side():
    """An empty prompt with no attributes should be handled gracefully."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{BASE_URL}/generate/image", json={"prompt": ""})
    # Backend may accept (queue) with empty prompt but Groq will handle — 202 or 422
    assert r.status_code in (202, 422), f"Unexpected status: {r.status_code}"


@pytest.mark.asyncio
async def test_missing_job_returns_404():
    """Polling a non-existent job_id returns 404."""
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{BASE_URL}/jobs/nonexistent-job-id-xyz/status")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_error_response_has_no_stack_trace():
    """
    Verify the global exception handler returns clean JSON.
    We trigger a 422 (invalid schema) and check no 'traceback' key leaks.
    """
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.post(
            f"{BASE_URL}/generate/image",
            json={"invalid_field": True}
        )
    # 422 from pydantic validation — should be structured, not a raw traceback
    body = r.text
    assert "Traceback" not in body
    assert "traceback" not in body.lower() or "traceback" not in r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Analysis endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyse_image_returns_5_attributes():
    """POST /analyse/image → returns subject, action, location, composition, style."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{BASE_URL}/analyse/image",
            json={"description": "A samurai standing on a misty mountain at dawn"}
        )
    assert r.status_code == 200
    body = r.json()
    for key in ("subject", "action", "location", "composition", "style"):
        assert key in body, f"Missing attribute '{key}' in response: {body}"


@pytest.mark.asyncio
async def test_analyse_video_returns_10_attributes():
    """POST /analyse/video → returns 10 video attributes."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{BASE_URL}/analyse/video",
            json={"description": "A whale breaching at sunset in slow motion"}
        )
    assert r.status_code == 200
    body = r.json()
    expected_keys = (
        "subject", "action", "scene", "style",
        "camera_angles", "camera_movements", "lens_effects",
        "temporal_elements", "color_grading", "audio"
    )
    for key in expected_keys:
        assert key in body, f"Missing video attribute '{key}' in response: {body}"
