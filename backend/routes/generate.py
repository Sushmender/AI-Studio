"""
generate.py — Generation endpoints.

POST /generate/image  → returns job_id immediately, runs fal.ai in background
POST /generate/video  → returns job_id immediately, runs Replicate in background

(fal_client and replicate_client will be wired in Day 1)
"""
import asyncio
from fastapi import APIRouter, HTTPException, Request

from backend.models.schemas import (
    GenerateRequest,
    GenerationMode,
    JobRecord,
    JobResponse,
    JobStatus,
)
from backend.services.job_store import job_store
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/generate", tags=["generation"])


async def _run_image_job(job_id: str, request: GenerateRequest) -> None:
    """Background task: will call fal_client in Day 1."""
    from backend.utils.logger import bind_job_context
    bind_job_context(job_id=job_id, provider="fal.ai", model="fal-ai/flux/dev", mode="image")

    await job_store.update_job(job_id, status=JobStatus.generating, provider="fal.ai", model="fal-ai/flux/dev")
    logger.info("image_job_started", prompt_length=len(request.prompt))

    # Placeholder — fal_client will be wired in Day 1
    logger.warning("fal_client_not_yet_wired", note="Day 1 task")
    await job_store.update_job(
        job_id,
        status=JobStatus.failed,
        error="fal.ai client not yet implemented — coming Day 1",
        error_type="not_implemented",
    )


async def _run_video_job(job_id: str, request: GenerateRequest) -> None:
    """Background task: will call replicate_client in Day 1."""
    from backend.utils.logger import bind_job_context
    bind_job_context(job_id=job_id, provider="replicate", model="luma/dream-machine", mode="video")

    await job_store.update_job(job_id, status=JobStatus.generating, provider="replicate", model="luma/dream-machine")
    logger.info("video_job_started", prompt_length=len(request.prompt))

    # Placeholder — replicate_client will be wired in Day 1
    logger.warning("replicate_client_not_yet_wired", note="Day 1 task")
    await job_store.update_job(
        job_id,
        status=JobStatus.failed,
        error="Replicate client not yet implemented — coming Day 1",
        error_type="not_implemented",
    )


@router.post("/image", response_model=JobResponse, status_code=202)
async def generate_image(request: GenerateRequest):
    """Submit an image generation job. Returns job_id for polling."""
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
async def generate_video(request: GenerateRequest):
    """Submit a video generation job. Returns job_id for polling."""
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
