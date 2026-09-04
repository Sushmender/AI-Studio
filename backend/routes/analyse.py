"""
analyse.py — Image attribute analysis endpoint.

POST /analyse/image
  → Groq Call 1: extracts 5 visual attributes from a raw user description
  → Returns attributes immediately for user editing (no job created)
"""
from fastapi import APIRouter, HTTPException, Request

from backend.clients.llm_client import analyse_image_attributes, analyse_video_attributes
from backend.models.schemas import AnalyseRequest, AnalyseResponse, VideoAnalyseRequest, VideoAnalyseResponse
from backend.services.rate_limiter import rate_limiter, RateLimitExceeded
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/analyse", tags=["analysis"])


@router.post(
    "/image",
    response_model=AnalyseResponse,
    summary="Analyse image description → extract 5 attributes",
    response_description="5 structured visual attributes ready for user editing",
)
async def analyse_image(body: AnalyseRequest, req: Request):
    """
    **Groq Call 1 (Image):** Parse a raw user description and extract the
    5 fundamental visual attributes used by fal.ai / FLUX Dev:

    | Attribute | Description |
    |-----------|-------------|
    | `subject` | Who or what is the main focus |
    | `action` | Pose, motion, or state |
    | `location` | Setting, environment, time of day |
    | `composition` | Camera angle, framing, depth of field, lighting |
    | `style` | Aesthetic, art movement, colour palette, mood |

    **Synchronous** — returns immediately. Does **not** create a generation job.
    The returned attributes are editable in the UI before the user confirms
    and triggers `POST /generate/image`.

    **Rate limit:** 10 requests per IP per 60-second window.
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


@router.post(
    "/video",
    response_model=VideoAnalyseResponse,
    summary="Analyse video description → extract 10 attributes",
    response_description="10 structured video attributes ready for user editing",
)
async def analyse_video(body: VideoAnalyseRequest, req: Request):
    """
    **Groq Call 1 (Video):** Parse a raw user description and extract
    10 video attributes across 3 groups:

    **Overall:** subject, action, scene, style, temporal_elements

    **Camera:** camera_angles, camera_movements, lens_effects

    **Audio** *(informational - Luma is visual-only):*
    dialogue, sound_effects

    **Synchronous** - returns immediately. Does **not** create a generation job.
    The returned attributes are editable in the UI before the user confirms
    and triggers ``POST /generate/video``.

    **Rate limit:** 10 requests per IP per 60-second window.
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
