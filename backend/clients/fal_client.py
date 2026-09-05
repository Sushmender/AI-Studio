"""
fal_client.py — fal.ai Image Generation Client
"""
import asyncio
import fal_client
from backend.config import get_settings
from backend.utils.logger import get_logger
from backend.utils.retry import async_retry, NonRetryableError, RetryableError

logger = get_logger(__name__)

@async_retry(max_attempts=2, backoff_base=1.5)
async def generate_image(prompt: str, width: int = 1024, height: int = 1024, num_inference_steps: int = 28, job_id: str = "") -> dict:
    settings = get_settings()
    
    if settings.mock_generation_apis:
        logger.info("mock_fal_generation", prompt=prompt)
        await asyncio.sleep(2)  # Simulate generation time
        return {"url": "https://fal.media/files/mock_image.png"}

    try:
        # Note: timeout is handled by the fal_client SDK, but we wrap it in a hard asyncio.wait_for just in case
        # Wait, the SDK has run_async that waits for the result
        res = await asyncio.wait_for(
            fal_client.run_async(
                settings.fal_image_model,
                arguments={
                    "prompt": prompt,
                    "image_size": {"width": width, "height": height},
                    "num_inference_steps": num_inference_steps,
                },
            ),
            timeout=settings.fal_timeout
        )
        
        # Typically fal returns an 'images' array containing dicts with 'url'
        if "images" in res and len(res["images"]) > 0:
            return {"url": res["images"][0]["url"]}
        return {"url": ""}
        
    except asyncio.TimeoutError as e:
        logger.error("fal_timeout", error=str(e))
        raise RetryableError("fal.ai timed out") from e
    except fal_client.FalClientHTTPError as e:
        logger.error("fal_http_error", error=str(e), status_code=e.status_code)
        if e.status_code and e.status_code >= 500:
            raise RetryableError(f"fal.ai server error: {e}") from e
        raise NonRetryableError(f"fal.ai error: {e}") from e
    except fal_client.FalClientError as e:
        logger.error("fal_client_error", error=str(e))
        raise NonRetryableError(f"fal.ai error: {e}") from e
    except Exception as e:
        logger.error("fal_unexpected_error", error=str(e))
        raise RetryableError(f"fal.ai unexpected error: {e}") from e
