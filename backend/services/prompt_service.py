"""
prompt_service.py — Orchestrates prompt enhancement via Groq.
"""
from typing import Literal, Tuple, Optional
from backend.clients.llm_client import enhance_prompt
from backend.utils.logger import get_logger

logger = get_logger(__name__)

async def enhance(raw: str, mode: Literal["image", "video"]) -> Tuple[str, Optional[str]]:
    """
    Returns (raw, enhanced).
    If Groq fails, logs a WARNING and falls through to raw (returns enhanced=None).
    """
    try:
        enhanced_res = await enhance_prompt(raw, mode)
        return raw, enhanced_res.enhanced_prompt
    except Exception as e:
        logger.warning(
            "groq_enhancement_failed",
            error=str(e),
            note="falling back to raw prompt",
        )
        return raw, None
