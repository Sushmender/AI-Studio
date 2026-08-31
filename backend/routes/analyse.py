"""
analyse.py — Image attribute analysis endpoint.

POST /analyse/image
  → Groq Call 1: extracts 5 visual attributes from a raw user description
  → Returns attributes immediately for user editing (no job created)
"""
from fastapi import APIRouter, HTTPException, Request

from backend.clients.groq_client import analyse_image_attributes, analyse_video_attributes
from backend.models.schemas import AnalyseRequest, AnalyseResponse, VideoAnalyseRequest, VideoAnalyseResponse
from backend.services.rate_limiter import rate_limiter, RateLimitExceeded
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/analyse", tags=["analysis"])


@router.post("/image", response_model=AnalyseResponse)
async def analyse_image(body: AnalyseRequest, req: Request):
    """
    Groq Call 1: Analyse a raw description and extract 5 visual attributes.
    Synchronous — returns immediately with the structured attributes.
    Does NOT create a generation job.
    """
    client_ip = req.client.host if req.client else "127.0.0.1"
    try:
        await rate_limiter.check(client_ip)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)},
        )

    logger.info("analyse_image_request", description_length=len(body.description))

    try:
        attributes = await analyse_image_attributes(body.description)
        logger.info(
            "analyse_image_done",
            subject_preview=attributes.subject[:40],
        )
        return AnalyseResponse(
            attributes=attributes,
            raw_description=body.description,
        )
    except Exception as e:
        logger.error("analyse_image_failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Image analysis failed — Groq could not process the description. Please try again.",
        )


@router.post("/video", response_model=VideoAnalyseResponse)
async def analyse_video(body: VideoAnalyseRequest, req: Request):
    """
    Groq Call 1 (Video): Analyse a raw description and extract 10 video attributes
    across 3 groups (Overall, Camera, Audio).
    Synchronous — returns immediately. Does NOT create a generation job.
    """
    client_ip = req.client.host if req.client else "127.0.0.1"
    try:
        await rate_limiter.check(client_ip)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)},
        )

    logger.info("analyse_video_request", description_length=len(body.description))

    try:
        attributes = await analyse_video_attributes(body.description)
        logger.info(
            "analyse_video_done",
            subject_preview=attributes.subject[:40],
            style_preview=attributes.style[:40],
        )
        return VideoAnalyseResponse(
            attributes=attributes,
            raw_description=body.description,
        )
    except Exception as e:
        logger.error("analyse_video_failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Video analysis failed — Groq could not process the description. Please try again.",
        )
