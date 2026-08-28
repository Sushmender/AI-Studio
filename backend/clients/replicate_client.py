"""
replicate_client.py — Replicate Video Generation Client
"""
import asyncio
import replicate
from backend.config import get_settings
from backend.utils.logger import get_logger
from backend.utils.retry import async_retry, NonRetryableError, RetryableError

logger = get_logger(__name__)

@async_retry(max_attempts=2, backoff_base=1.5)
async def generate_video(prompt: str, aspect_ratio: str = "16:9", duration: int = 5, job_id: str = "") -> dict:
    settings = get_settings()
    
    if settings.mock_apis:
        logger.info("mock_replicate_generation", prompt=prompt)
        await asyncio.sleep(4)  # Simulate some processing time
        return {"url": "https://replicate.delivery/pbxt/mock_video.mp4"}

    try:
        # replicate handles retries and polling internally in run(), but we enforce timeout
        # Using async replicate API:
        # Note: replicate currently relies on the REPLICATE_API_TOKEN environment variable being set.
        res = await asyncio.wait_for(
            replicate.async_run(
                settings.replicate_video_model,
                input={
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "duration": duration,
                }
            ),
            timeout=settings.replicate_timeout
        )
        # Result is typically a URL string or list of URL strings for video models.
        if isinstance(res, list) and len(res) > 0:
            return {"url": str(res[0])}
        elif isinstance(res, str):
             return {"url": res}
        return {"url": str(res)}
        
    except asyncio.TimeoutError as e:
        logger.error("replicate_timeout", error=str(e))
        raise RetryableError(f"Replicate returned a timeout (generation exceeded {settings.replicate_timeout} seconds)") from e
    except replicate.exceptions.ReplicateError as e:
        # We can map specific Replicate errors
        raise NonRetryableError(f"Replicate generation failed: {e}") from e
    except Exception as e:
        logger.error("replicate_unexpected_error", error=str(e))
        raise RetryableError(f"Replicate unexpected error: {e}") from e
