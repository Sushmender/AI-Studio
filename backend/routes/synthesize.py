"""
synthesize.py — Synchronous prompt synthesis endpoint.

POST /synthesize
  → Takes attributes or raw prompt, runs Groq synthesis, and returns final_prompt.
  → Used as the intermediate "Review Prompt" step before media generation.
"""
from fastapi import APIRouter, HTTPException, Request

from backend.clients.llm_client import synthesize_image_prompt, synthesize_video_prompt, PromptSynthesisError
from backend.models.schemas import GenerationMode, SynthesizeRequest, SynthesizeResponse
from backend.services.prompt_service import enhance
from backend.services.rate_limiter import rate_limiter, RateLimitExceeded
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/synthesize", tags=["synthesis"])


@router.post(
    "",
    response_model=SynthesizeResponse,
    summary="Synthesize prompt from attributes or raw description",
    response_description="The final synthesized prompt ready for user review",
)
async def synthesize_prompt(body: SynthesizeRequest, req: Request):
    """
    Synthesize an optimised prompt for image or video generation.

    If attributes are provided, Groq synthesises them into an optimised prompt.
    If only a prompt is provided, Groq enhances the raw prompt.

    **Synchronous** — returns the prompt string. Does **not** create a generation job.
    
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

    logger.info("synthesize_prompt_request", mode=body.mode)

    try:
        if body.mode == GenerationMode.image:
            if body.attributes is not None:
                final_prompt = await synthesize_image_prompt(body.attributes)
            else:
                final_result = await enhance(body.prompt, "image")
                final_prompt = final_result.final_prompt if final_result.final_prompt else final_result.raw_prompt
        else:
            if body.video_attributes is not None:
                final_prompt = await synthesize_video_prompt(body.video_attributes)
            else:
                final_result = await enhance(body.prompt, "video")
                final_prompt = final_result.final_prompt if final_result.final_prompt else final_result.raw_prompt

        logger.info("synthesize_endpoint_success", mode=body.mode, length=len(final_prompt))
        return SynthesizeResponse(final_prompt=final_prompt)

    except PromptSynthesisError as e:
        # PromptSynthesisError is already logged in llm_client with the raw_text
        raise HTTPException(
            status_code=502,
            detail="Prompt synthesis failed, please retry.",
        )
    except Exception as e:
        logger.error("synthesize_endpoint_failed", error=str(e))
        raise HTTPException(
            status_code=502,
            detail="Prompt synthesis failed — Groq could not process the request. Please try again.",
        )
