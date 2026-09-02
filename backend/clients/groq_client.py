"""
groq_client.py — Groq Prompt Enhancement Client
"""
import asyncio
import json
from typing import Any, Literal
from groq import AsyncGroq, RateLimitError
from backend.config import get_settings
from backend.utils.logger import get_logger
from backend.utils.retry import async_retry, RetryableError
from backend.models.schemas import EnhancedPrompt, ImageAttributes, VideoAttributes

logger = get_logger(__name__)

_FALLBACK_MODEL = "llama-3.1-8b-instant"


async def _chat_with_fallback(client: AsyncGroq, primary_model: str, timeout: float, **kwargs: Any) -> Any:
    """
    Try primary_model first. If Groq returns RateLimitError (quota exceeded),
    automatically retry once with the fallback model.
    All other exceptions propagate normally.
    """
    try:
        return await asyncio.wait_for(
            client.chat.completions.create(model=primary_model, **kwargs),
            timeout=timeout,
        )
    except RateLimitError:
        logger.warning(
            "groq_model_fallback",
            primary_model=primary_model,
            fallback_model=_FALLBACK_MODEL,
            reason="quota_exceeded",
        )
        return await asyncio.wait_for(
            client.chat.completions.create(model=_FALLBACK_MODEL, **kwargs),
            timeout=timeout,
        )


def _extract_json(text: str) -> dict:
    """Parse JSON from a Groq response, stripping markdown, conversational text, and <think> blocks.
    Finds the first '{' and last '}' to extract just the JSON object.
    """
    text = text.strip()
    
    # Strip <think>...</think> chain-of-thought block if present (common with Qwen models)
    if "<think>" in text:
        end_think = text.find("</think>")
        if end_think != -1:
            text = text[end_think + 8:].strip()
        else:
            # Malformed or truncated think block, try to just clear everything before the last }
            # Wait, if it's truncated, the JSON isn't even there. But let's fallback cleanly.
            pass
            
    # Try to find JSON boundaries
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx + 1]
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("json_extraction_failed", raw_text=text, error=str(e))
        raise e

SYSTEM_PROMPTS = {
    "image": "You are a world-class image prompt engineer. Rewrite the user's prompt to be richly descriptive: include lighting, composition, style, color palette, and mood. Keep it under 200 words. Return only the enhanced prompt, no explanation.",
    "video": "You are a world-class video prompt engineer. Rewrite the user's prompt to describe motion, pacing, camera movement, scene transitions, and visual atmosphere. Keep it under 150 words. Return only the enhanced prompt, no explanation."
}

@async_retry(max_attempts=2, backoff_base=1.5)
async def enhance_prompt(raw: str, mode: Literal["image", "video"]) -> EnhancedPrompt:
    settings = get_settings()

    try:
        # Initialize Groq client. Uses GROQ_API_KEY from environment automatically if set
        client = AsyncGroq(api_key=settings.groq_api_key)
        
        system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["image"])
        
        completion = await _chat_with_fallback(
            client,
            primary_model=settings.groq_model,
            timeout=settings.groq_timeout,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw},
            ],
            temperature=0.7,
            max_tokens=300,
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


# ── Groq Call 1: Analyse description → 5 structured attributes ───────────────────

ANALYSE_SYSTEM_PROMPT = """\
You are a professional image director and visual prompt engineer.

The user will give you a natural language description of an image they want generated.
Your job is to extract and infer exactly 5 creative attributes from their description.

Rules:
- Even if the user hasn't mentioned an attribute, you MUST invent a suitable value that
  fits the overall aesthetic coherently.
- Be specific, evocative, and cinematically aware.
- Keep each value under 25 words.

Respond with ONLY a JSON object — no markdown, no explanation — in this exact format:
{
  "subject":     "<who or what is the main focus>",
  "action":      "<what is happening or the pose/state>",
  "location":    "<the setting, environment, and time of day>",
  "composition": "<camera angle, framing, depth of field, lighting setup>",
  "style":       "<overall aesthetic, art movement, color palette, mood>"
}
"""

_ATTRIBUTE_KEYS = {"subject", "action", "location", "composition", "style"}
_FALLBACK_ATTRIBUTES = {
    "subject":     "A main subject fitting the described scene",
    "action":      "Standing naturally in the environment",
    "location":    "An environment that matches the described mood",
    "composition": "Eye-level shot, balanced framing, natural lighting",
    "style":       "Cinematic realism, neutral color palette, photographic quality",
}


async def analyse_image_attributes(description: str) -> ImageAttributes:
    """Groq Call 1: Analyse a raw user description and extract 5 image attributes."""
    settings = get_settings()

    client = AsyncGroq(api_key=settings.groq_api_key)
    try:
        completion = await _chat_with_fallback(
            client,
            primary_model=settings.groq_model,
            timeout=settings.groq_timeout,
            messages=[
                {"role": "system", "content": ANALYSE_SYSTEM_PROMPT},
                {"role": "user", "content": description},
            ],
            temperature=0.75,
            max_tokens=2000,
        )

        raw_json = completion.choices[0].message.content.strip()
        data = _extract_json(raw_json)

        # Ensure all 5 keys are present; fill missing with sensible fallbacks
        attrs = {k: data.get(k, _FALLBACK_ATTRIBUTES[k]) for k in _ATTRIBUTE_KEYS}
        return ImageAttributes(**attrs)

    except asyncio.TimeoutError as e:
        logger.error("groq_analyse_timeout", error=str(e))
        raise RetryableError("Image analysis timed out") from e
    except json.JSONDecodeError as e:
        logger.error("groq_analyse_json_error", error=str(e))
        raise RetryableError("Failed to parse analysis response") from e
    except Exception as e:
        logger.error("groq_analyse_error", error=str(e))
        raise RetryableError(f"Image analysis failed: {e}") from e


# ── Groq Call 2: Synthesize attributes → optimized image prompt ─────────────────

SYNTHESIZE_SYSTEM_PROMPT = """\
You are a master AI image prompt engineer working with diffusion models.

You will receive 5 structured visual attributes for an image. Your job is to synthesize
these into a single, highly effective image generation prompt.

Rules:
- Weave all 5 attributes together naturally — do NOT list them as labels.
- Be vivid, specific, and rich with sensory detail.
- The prompt should read as a single flowing paragraph.
- Keep it between 60–120 words.
- Do NOT include any explanation, preamble, or labels — return ONLY the prompt text.
"""


async def synthesize_image_prompt(attributes: ImageAttributes) -> str:
    """Groq Call 2: Synthesize the user-confirmed attributes into an optimized fal.ai prompt."""
    settings = get_settings()

    client = AsyncGroq(api_key=settings.groq_api_key)
    attribute_text = (
        f"SUBJECT: {attributes.subject}\n"
        f"ACTION: {attributes.action}\n"
        f"LOCATION: {attributes.location}\n"
        f"COMPOSITION: {attributes.composition}\n"
        f"STYLE: {attributes.style}"
    )

    try:
        completion = await _chat_with_fallback(
            client,
            primary_model=settings.groq_model,
            timeout=settings.groq_timeout,
            messages=[
                {"role": "system", "content": SYNTHESIZE_SYSTEM_PROMPT},
                {"role": "user", "content": attribute_text},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        return completion.choices[0].message.content.strip()

    except asyncio.TimeoutError as e:
        logger.error("groq_synthesize_timeout", error=str(e))
        raise RetryableError("Prompt synthesis timed out") from e
    except Exception as e:
        logger.error("groq_synthesize_error", error=str(e))
        raise RetryableError(f"Prompt synthesis failed: {e}") from e


# ── Groq Call 1 (Video): Analyse description → 10 structured attributes ──────────

VIDEO_ANALYSE_SYSTEM_PROMPT = """\
You are a professional film director, cinematographer, and video prompt engineer.

The user will give you a natural language description of a video they want generated.
Your job is to extract and infer exactly 10 creative attributes across 3 groups.

Rules:
- Even if an attribute is not mentioned, you MUST invent a suitable value that fits
  the overall aesthetic and narrative coherently.
- Be specific, evocative, and cinematically precise.
- Keep each value under 30 words.
- For DIALOGUE: describe what might be said, or write "No dialogue — ambient sound only" if silent.
- For SOUND_EFFECTS: describe key sounds, or write "Natural ambient sounds" if nothing specific.

Respond with ONLY a JSON object — no markdown, no explanation — with these exact keys:
{
  "subject":           "<who or what is the main focus of the video>",
  "action":            "<what is happening — motion, behavior, narrative arc>",
  "scene":             "<when and where — setting, environment, time of day, weather>",
  "style":             "<artistic filter / aesthetic: cinematic, documentary, animated, etc.>",
  "temporal_elements": "<time-based changes: slow-mo, time-lapse, transitions, pacing rhythm>",
  "camera_angles":     "<shot viewpoints: wide, close-up, bird's eye, dutch angle, etc.>",
  "camera_movements":  "<dynamic experience: dolly, pan, handheld, steadicam, drone, etc.>",
  "lens_effects":      "<how camera sees: bokeh, anamorphic, rack focus, lens flare, etc.>",
  "dialogue":          "<spoken words or voice-over in the scene>",
  "sound_effects":     "<distinct sounds that occur: wind, crowd, footsteps, etc.>"
}
"""

_VIDEO_ATTRIBUTE_KEYS = {
    "subject", "action", "scene", "style", "temporal_elements",
    "camera_angles", "camera_movements", "lens_effects", "dialogue", "sound_effects",
}

_VIDEO_FALLBACK_ATTRIBUTES = {
    "subject":           "A main subject fitting the described scene",
    "action":            "Moving naturally within the environment",
    "scene":             "An environment that matches the described mood, daytime",
    "style":             "Cinematic realism, natural color grading",
    "temporal_elements": "Real-time pacing, no slow-motion, smooth transitions",
    "camera_angles":     "Eye-level medium shot, balanced framing",
    "camera_movements":  "Slow dolly-in, subtle handheld warmth",
    "lens_effects":      "Shallow depth of field, natural bokeh",
    "dialogue":          "No dialogue — ambient sound only",
    "sound_effects":     "Natural ambient sounds matching the environment",
}


async def analyse_video_attributes(description: str) -> VideoAttributes:
    """Groq Call 1 (Video): Analyse a raw description and extract 10 video attributes."""
    settings = get_settings()

    client = AsyncGroq(api_key=settings.groq_api_key)
    try:
        completion = await _chat_with_fallback(
            client,
            primary_model=settings.groq_model,
            timeout=settings.groq_timeout,
            messages=[
                {"role": "system", "content": VIDEO_ANALYSE_SYSTEM_PROMPT},
                {"role": "user", "content": description},
            ],
            temperature=0.75,
            max_tokens=2000,
        )

        raw_json = completion.choices[0].message.content.strip()
        data = _extract_json(raw_json)

        # Ensure all 10 keys are present; fill missing with sensible fallbacks
        attrs = {k: data.get(k, _VIDEO_FALLBACK_ATTRIBUTES[k]) for k in _VIDEO_ATTRIBUTE_KEYS}
        return VideoAttributes(**attrs)

    except asyncio.TimeoutError as e:
        logger.error("groq_video_analyse_timeout", error=str(e))
        raise RetryableError("Video analysis timed out") from e
    except json.JSONDecodeError as e:
        logger.error("groq_video_analyse_json_error", error=str(e))
        raise RetryableError("Failed to parse video analysis response") from e
    except Exception as e:
        logger.error("groq_video_analyse_error", error=str(e))
        raise RetryableError(f"Video analysis failed: {e}") from e


# ── Groq Call 2 (Video): Synthesize attributes → optimized Replicate prompt ────────

VIDEO_SYNTHESIZE_SYSTEM_PROMPT = """\
You are a master AI video generation prompt engineer for diffusion-based video models.

You will receive 10 structured video attributes across 3 groups (Overall, Camera, Audio).
Your job is to synthesize these into a single, highly effective video generation prompt.

Rules:
- Weave OVERALL and CAMERA attributes naturally into flowing prose — do NOT use labels.
- Incorporate AUDIO attributes to imply atmosphere and energy in the visuals
  (the model is visual-only — audio fields guide the scene's mood, not literal sound).
- Be vivid, specific, cinematic, and motion-aware.
- The prompt should read as a single flowing paragraph describing the video.
- Keep it between 80–150 words.
- Do NOT include labels, section headers, or any explanation — return ONLY the prompt text.
"""


async def synthesize_video_prompt(attributes: VideoAttributes) -> str:
    """Groq Call 2 (Video): Synthesize the user-confirmed 10 attributes into an optimized Replicate prompt."""
    settings = get_settings()

    client = AsyncGroq(api_key=settings.groq_api_key)
    attribute_text = (
        f"OVERALL\n"
        f"  Subject:            {attributes.subject}\n"
        f"  Action:             {attributes.action}\n"
        f"  Scene:              {attributes.scene}\n"
        f"  Style:              {attributes.style}\n"
        f"  Temporal Elements:  {attributes.temporal_elements}\n\n"
        f"CAMERA\n"
        f"  Camera Angles:    {attributes.camera_angles}\n"
        f"  Camera Movements: {attributes.camera_movements}\n"
        f"  Lens Effects:     {attributes.lens_effects}\n\n"
        f"AUDIO (visual mood guidance only)\n"
        f"  Dialogue:       {attributes.dialogue}\n"
        f"  Sound Effects:  {attributes.sound_effects}"
    )

    try:
        completion = await _chat_with_fallback(
            client,
            primary_model=settings.groq_model,
            timeout=settings.groq_timeout,
            messages=[
                {"role": "system", "content": VIDEO_SYNTHESIZE_SYSTEM_PROMPT},
                {"role": "user", "content": attribute_text},
            ],
            temperature=0.7,
            max_tokens=250,
        )
        return completion.choices[0].message.content.strip()

    except asyncio.TimeoutError as e:
        logger.error("groq_video_synthesize_timeout", error=str(e))
        raise RetryableError("Video prompt synthesis timed out") from e
    except Exception as e:
        logger.error("groq_video_synthesize_error", error=str(e))
        raise RetryableError(f"Video prompt synthesis failed: {e}") from e
