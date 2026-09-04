"""
generate.py — Generation endpoints.

POST /generate/image  → returns job_id immediately, runs fal.ai in background
POST /generate/video  → returns job_id immediately, runs Replicate in background
"""
import asyncio
import time
from fastapi import APIRouter, HTTPException, Request

from backend.models.schemas import (
    GenerateRequest,
    GenerationMode,
    JobRecord,
    JobResponse,
    JobStatus,
)
from backend.services.job_store import job_store
from backend.utils.logger import get_logger, bind_job_context
from backend.clients import fal_client, replicate_client
from backend.clients.llm_client import synthesize_image_prompt, synthesize_video_prompt
from backend.services.prompt_service import enhance
from backend.services.rate_limiter import rate_limiter, RateLimitExceeded
from backend.utils.tasks import log_task_exception


logger = get_logger(__name__)
router = APIRouter(prefix="/generate", tags=["generation"])


async def _run_image_job(job_id: str, request: GenerateRequest) -> None:
    bind_job_context(job_id=job_id, provider="fal.ai", model="fal-ai/flux/dev", mode="image")
    await job_store.update_job(job_id, status=JobStatus.generating, provider="fal.ai", model="fal-ai/flux/dev")
    logger.info("image_job_started", prompt_length=len(request.prompt))

    start = time.monotonic()

    # ── Prompt resolution: 3-stage pipeline vs legacy enhance ─────────────────
    if request.attributes is not None:
        # Stage 2 of the structured pipeline:
        # Groq Call 2 — synthesize the user-confirmed attributes into an optimised prompt
        logger.info("image_job_synthesizing", subject=request.attributes.subject[:40])
        try:
            synthesized = await synthesize_image_prompt(request.attributes)
            prompt_to_use = synthesized
            raw_prompt = request.prompt or f"Structured: {request.attributes.subject}"
            await job_store.update_job(
                job_id,
                raw_prompt=raw_prompt,
                enhanced_prompt=synthesized,
            )
            logger.info("image_job_synthesized", prompt_preview=synthesized[:80])
        except Exception as e:
            # Groq Call 2 failed — fall back to compiling attributes manually
            logger.warning(
                "groq_synthesize_failed_fallback",
                error=str(e),
                note="compiling attributes manually",
            )
            attrs = request.attributes
            prompt_to_use = (
                f"{attrs.subject}. {attrs.action}. "
                f"Set in {attrs.location}. "
                f"Shot with {attrs.composition}. "
                f"Style: {attrs.style}."
            )
            raw_prompt = request.prompt or f"Structured: {attrs.subject}"
            await job_store.update_job(
                job_id,
                raw_prompt=raw_prompt,
                enhanced_prompt=prompt_to_use,
            )
    else:
        # Legacy path: enhance raw prompt via Groq
        raw_prompt, enhanced_prompt = await enhance(request.prompt, "image")
        await job_store.update_job(job_id, enhanced_prompt=enhanced_prompt)
        prompt_to_use = enhanced_prompt if enhanced_prompt else raw_prompt

    # ── Stage 3: fal.ai generates the image ────────────────────────────────────
    try:
        res = await fal_client.generate_image(
            prompt=prompt_to_use,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_inference_steps,
            job_id=job_id
        )
        latency_ms = (time.monotonic() - start) * 1000
        await job_store.update_job(
            job_id,
            status=JobStatus.done,
            result_url=res.get("url"),
            latency_ms=latency_ms
        )
        logger.info("image_job_done", latency_ms=latency_ms)
    except Exception as e:
        latency_ms = (time.monotonic() - start) * 1000
        logger.error("image_job_failed", error=str(e), latency_ms=latency_ms)
        await job_store.update_job(
            job_id,
            status=JobStatus.failed,
            error=str(e),
            error_type=type(e).__name__,
            latency_ms=latency_ms
        )


async def _run_video_job(job_id: str, request: GenerateRequest) -> None:
    bind_job_context(job_id=job_id, provider="replicate", model="luma/ray-flash-2-720p", mode="video")
    await job_store.update_job(job_id, status=JobStatus.generating, provider="replicate", model="luma/ray-flash-2-720p")
    logger.info("video_job_started", prompt_length=len(request.prompt))

    start = time.monotonic()

    # ── Prompt resolution: 3-stage pipeline vs legacy enhance ─────────────────
    if request.video_attributes is not None:
        # Stage 2 of the structured video pipeline:
        # Groq Call 2 — synthesize the user-confirmed 10 attributes into an optimised prompt
        logger.info("video_job_synthesizing", subject=request.video_attributes.subject[:40])
        try:
            synthesized = await synthesize_video_prompt(request.video_attributes)
            prompt_to_use = synthesized
            raw_prompt = request.prompt or f"Structured video: {request.video_attributes.subject}"
            await job_store.update_job(
                job_id,
                raw_prompt=raw_prompt,
                enhanced_prompt=synthesized,
            )
            logger.info("video_job_synthesized", prompt_preview=synthesized[:80])
        except Exception as e:
            # Groq Call 2 failed — fall back to manually compiling attributes
            logger.warning(
                "groq_video_synthesize_failed_fallback",
                error=str(e),
                note="compiling attributes manually",
            )
            attrs = request.video_attributes
            prompt_to_use = (
                f"{attrs.subject}. {attrs.action}. "
                f"Set in {attrs.scene}. "
                f"{attrs.style} aesthetic. "
                f"Shot with {attrs.camera_angles}, {attrs.camera_movements}. "
                f"{attrs.lens_effects}. "
                f"Pacing: {attrs.temporal_elements}."
            )
            raw_prompt = request.prompt or f"Structured video: {attrs.subject}"
            await job_store.update_job(
                job_id,
                raw_prompt=raw_prompt,
                enhanced_prompt=prompt_to_use,
            )
    else:
        # Legacy path: Groq enhance_prompt for video
        raw_prompt, enhanced_prompt = await enhance(request.prompt, "video")
        await job_store.update_job(job_id, enhanced_prompt=enhanced_prompt)
        prompt_to_use = enhanced_prompt if enhanced_prompt else raw_prompt

    # ── Stage 3: Replicate generates the video ──────────────────────────────────
    try:
        res = await replicate_client.generate_video(
            prompt=prompt_to_use,
            aspect_ratio=request.aspect_ratio,
            duration=request.duration,
            job_id=job_id
        )
        latency_ms = (time.monotonic() - start) * 1000
        await job_store.update_job(
            job_id,
            status=JobStatus.done,
            result_url=res.get("url"),
            latency_ms=latency_ms
        )
        logger.info("video_job_done", latency_ms=latency_ms)
    except Exception as e:
        latency_ms = (time.monotonic() - start) * 1000
        logger.error("video_job_failed", error=str(e), latency_ms=latency_ms)
        await job_store.update_job(
            job_id,
            status=JobStatus.failed,
            error=str(e),
            error_type=type(e).__name__,
            latency_ms=latency_ms
        )


@router.post(
    "/image",
    response_model=JobResponse,
    status_code=202,
    summary="Submit an image generation job",
    response_description="Job queued — use job_id to poll status",
)
async def generate_image(request: GenerateRequest, req: Request):
    """
    Submit an asynchronous image generation job using **fal.ai / FLUX Dev**.

    **Two prompt modes:**
    - **Structured** (`attributes` field present): Groq Call 2 synthesises an
      optimised fal.ai prompt from the 5 user-confirmed image attributes.
    - **Legacy** (`prompt` only): Groq enhances the raw prompt before generation.

    Returns a `job_id` immediately (HTTP 202). Poll `GET /jobs/{id}/status`
    every 2 seconds until `status` is `done` or `failed`, then fetch the
    result from `GET /jobs/{id}/result`.

    **Rate limit:** 10 requests per IP per 60-second sliding window.
    Exceeding the limit returns HTTP 429 with a `Retry-After` header.
    """
    # Rate Limit
    client_ip = req.client.host if req.client else "127.0.0.1"
    try:
        await rate_limiter.check(client_ip)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)}
        )

    # Determine display prompt for the job record
    display_prompt = (
        request.prompt
        if request.prompt
        else f"Structured image: {request.attributes.subject}"
        if request.attributes
        else "(no prompt)"
    )

    record = JobRecord(
        mode=GenerationMode.image,
        raw_prompt=display_prompt,
        provider="fal.ai",
        model="fal-ai/flux/dev",
    )
    await job_store.create_job(record)
    asyncio.create_task(_run_image_job(record.job_id, request)).add_done_callback(log_task_exception)
    logger.info("image_job_queued", job_id=record.job_id, has_attributes=request.attributes is not None)
    return JobResponse(
        job_id=record.job_id,
        status=JobStatus.queued,
        mode=GenerationMode.image,
        raw_prompt=display_prompt,
        message="Image generation job queued",
    )


@router.post(
    "/video",
    response_model=JobResponse,
    status_code=202,
    summary="Submit a video generation job",
    response_description="Job queued — use job_id to poll status",
)
async def generate_video(request: GenerateRequest, req: Request):
    """
    Submit an asynchronous video generation job using **Replicate / Luma Ray Flash 2 720p**.

    **Two prompt modes:**
    - **Structured** (`video_attributes` field present): Groq synthesises a
      cinematic prompt from all 10 video attributes (subject, action, scene,
      style, camera angles/movements/lens, temporal elements, dialogue, sound effects).
    - **Legacy** (`prompt` only): Groq enhances the raw prompt for Replicate.

    Video generation typically takes **2–5 minutes**. The response includes
    `estimated_wait_seconds` to drive a progress indicator in the UI.
    Poll `GET /jobs/{id}/status` every 5 seconds.

    **Rate limit:** 10 requests per IP per 60-second sliding window.
    """
    # Rate Limit
    client_ip = req.client.host if req.client else "127.0.0.1"
    try:
        await rate_limiter.check(client_ip)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)}
        )

    record = JobRecord(
        mode=GenerationMode.video,
        raw_prompt=request.prompt,
        provider="replicate",
        model="luma/ray-flash-2-720p",
        estimated_wait_seconds=180,  # 2-5 min — show in UI
    )
    await job_store.create_job(record)
    asyncio.create_task(_run_video_job(record.job_id, request)).add_done_callback(log_task_exception)
    logger.info("video_job_queued", job_id=record.job_id)
    return JobResponse(
        job_id=record.job_id,
        status=JobStatus.queued,
        mode=GenerationMode.video,
        raw_prompt=request.prompt,
        message="Video generation job queued — may take 2–5 minutes",
        estimated_wait_seconds=180,
    )
