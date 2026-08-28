"""
groq_client.py — Groq Prompt Enhancement Client
"""
import asyncio
from typing import Literal
from groq import AsyncGroq
from backend.config import get_settings
from backend.utils.logger import get_logger
from backend.utils.retry import async_retry, NonRetryableError, RetryableError
from backend.models.schemas import EnhancedPrompt

logger = get_logger(__name__)

SYSTEM_PROMPTS = {
    "image": "You are a world-class image prompt engineer. Rewrite the user's prompt to be richly descriptive: include lighting, composition, style, color palette, and mood. Keep it under 200 words. Return only the enhanced prompt, no explanation.",
    "video": "You are a world-class video prompt engineer. Rewrite the user's prompt to describe motion, pacing, camera movement, scene transitions, and visual atmosphere. Keep it under 150 words. Return only the enhanced prompt, no explanation."
}

@async_retry(max_attempts=2, backoff_base=1.5)
async def enhance_prompt(raw: str, mode: Literal["image", "video"]) -> EnhancedPrompt:
    settings = get_settings()
    
    if settings.mock_apis:
        logger.info("mock_groq_enhancement", prompt=raw)
        await asyncio.sleep(0.5)
        return EnhancedPrompt(
            raw_prompt=raw,
            enhanced_prompt=f"MOCKED ENHANCED {mode.upper()} PROMPT: {raw} with cinematic lighting, 8k resolution, photorealistic"
        )

    try:
        # Initialize Groq client. Uses GROQ_API_KEY from environment automatically if set
        client = AsyncGroq(api_key=settings.groq_api_key)
        
        system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["image"])
        
        completion = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw}
                ],
                temperature=0.7,
                max_tokens=300,
            ),
            timeout=settings.groq_timeout
        )
        
        enhanced_text = completion.choices[0].message.content.strip()
        
        return EnhancedPrompt(
            raw_prompt=raw,
            enhanced_prompt=enhanced_text
        )
        
    except asyncio.TimeoutError as e:
        logger.error("groq_timeout", error=str(e))
        raise RetryableError("Prompt enhancement timed out") from e
    except Exception as e:
        logger.error("groq_unexpected_error", error=str(e))
        raise RetryableError(f"Groq unexpected error: {e}") from e
