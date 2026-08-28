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
from backend.services.prompt_service import enhance
from backend.services.rate_limiter import rate_limiter, RateLimitExceeded


logger = get_logger(__name__)
router = APIRouter(prefix="/generate", tags=["generation"])


async def _run_image_job(job_id: str, request: GenerateRequest) -> None:
    bind_job_context(job_id=job_id, provider="fal.ai", model="fal-ai/flux/dev", mode="image")
    await job_store.update_job(job_id, status=JobStatus.generating, provider="fal.ai", model="fal-ai/flux/dev")
    logger.info("image_job_started", prompt_length=len(request.prompt))

    start = time.monotonic()
    
    # 1. Enhance Prompt
    raw_prompt, enhanced_prompt = await enhance(request.prompt, "image")
    await job_store.update_job(job_id, enhanced_prompt=enhanced_prompt)
    
    prompt_to_use = enhanced_prompt if enhanced_prompt else raw_prompt

    # 2. Generate Image
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
    bind_job_context(job_id=job_id, provider="replicate", model="luma/dream-machine", mode="video")
    await job_store.update_job(job_id, status=JobStatus.generating, provider="replicate", model="luma/dream-machine")
    logger.info("video_job_started", prompt_length=len(request.prompt))

    start = time.monotonic()

    # 1. Enhance Prompt
    raw_prompt, enhanced_prompt = await enhance(request.prompt, "video")
    await job_store.update_job(job_id, enhanced_prompt=enhanced_prompt)
    
    prompt_to_use = enhanced_prompt if enhanced_prompt else raw_prompt

    # 2. Generate Video
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


@router.post("/image", response_model=JobResponse, status_code=202)
async def generate_image(request: GenerateRequest, req: Request):
    """Submit an image generation job. Returns job_id for polling."""
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
        mode=GenerationMode.image,
        raw_prompt=request.prompt,
        provider="fal.ai",
        model="fal-ai/flux/dev",
    )
    await job_store.create_job(record)
    asyncio.create_task(_run_image_job(record.job_id, request))
    logger.info("image_job_queued", job_id=record.job_id)
    return JobResponse(
        job_id=record.job_id,
        status=JobStatus.queued,
        mode=GenerationMode.image,
        raw_prompt=request.prompt,
        message="Image generation job queued",
    )


@router.post("/video", response_model=JobResponse, status_code=202)
async def generate_video(request: GenerateRequest, req: Request):
    """Submit a video generation job. Returns job_id for polling."""
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
        model="luma/dream-machine",
        estimated_wait_seconds=180,  # 2-5 min — show in UI
    )
    await job_store.create_job(record)
    asyncio.create_task(_run_video_job(record.job_id, request))
    logger.info("video_job_queued", job_id=record.job_id)
    return JobResponse(
        job_id=record.job_id,
        status=JobStatus.queued,
        mode=GenerationMode.video,
        raw_prompt=request.prompt,
        message="Video generation job queued — may take 2–5 minutes",
        estimated_wait_seconds=180,
    )
