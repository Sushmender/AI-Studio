"""
llm_client.py — LLM Prompt Enhancement Client
"""
import asyncio
import json
import re
from typing import Any, Literal
from groq import AsyncGroq, RateLimitError
from backend.config import get_settings
from backend.utils.logger import get_logger
from backend.utils.retry import async_retry, RetryableError
from backend.models.schemas import FinalPrompt, ImageAttributes, VideoAttributes

logger = get_logger(__name__)

class PromptSynthesisError(Exception):
    """Raised when prompt synthesis extraction fails after all stages."""
    pass

_FALLBACK_MODEL = "llama-3.1-8b-instant"


import httpx

class MockMessage:
    def __init__(self, content):
        self.content = content

class MockChoice:
    def __init__(self, message):
        self.message = message
        
class MockCompletion:
    def __init__(self, choices):
        self.choices = choices

async def _chat_with_fallback(client: AsyncGroq, primary_model: str, timeout: float, **kwargs: Any) -> Any:
    """
    Try primary_model first. If Groq returns RateLimitError (quota exceeded),
    automatically retry once with the fallback model.
    All other exceptions propagate normally.
    """
    settings = get_settings()
    provider = settings.llm_provider.upper()

    if provider == "OPENROUTER":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.openrouter_api_key}",
        }
        
        payload = {
            "model": settings.openrouter_model,
            "messages": kwargs.get("messages", []),
            "temperature": kwargs.get("temperature", 0.7),
            "response_format": {"type": "json_object"},
        }
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
            
        async with httpx.AsyncClient(timeout=timeout) as httpx_client:
            resp = await httpx_client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            content = data["choices"][0]["message"]["content"]
            return MockCompletion([MockChoice(MockMessage(content))])
    else:
        try:
            return await asyncio.wait_for(
                client.chat.completions.create(model=primary_model, response_format={"type": "json_object"}, **kwargs),
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
                client.chat.completions.create(model=_FALLBACK_MODEL, response_format={"type": "json_object"}, **kwargs),
                timeout=timeout,
            )

def strip_think_block(text: str) -> str:
    """Strip <think>...</think> chain-of-thought block if present."""
    text = text.strip()
    if "<think>" in text:
        end_think = text.find("</think>")
        if end_think != -1:
            text = text[end_think + 8:].strip()
    return text


def clean_text_prompt(text: str) -> str:
    """
    Clean the text prompt from conversational preamble and <think> blocks.
    If the response ends with a quoted paragraph or contains it as a distinct block,
    extract only the quoted paragraph and discard the reasoning before it.
    """
    text = strip_think_block(text)
    
    import re
    # Remove markdown code blocks if the LLM wrapped it in ```
    md_match = re.search(r'```(?:[a-zA-Z]*\n)?(.*?)```', text, re.DOTALL)
    if md_match:
        text = md_match.group(1).strip()
        
    # Extract quoted text if the LLM wrapped the whole response in quotes
    # or if it ends with a quoted paragraph.
    # Look for quotes that contain more than just a few words, typically at the end.
    quote_match = re.search(r'["\'](.*?)[."\']*\s*$', text, re.DOTALL)
    if quote_match:
        extracted = quote_match.group(1).strip()
        if len(extracted.split()) > 10:
            return extracted

    # Fallback: if there's a preamble like "Here is the prompt:\n\n"
    # or "Draft:", we can split by double newline or 'Draft:' and take the last part.
    if "Draft:" in text:
        return text.split("Draft:")[-1].strip().strip('"\'')
        
    parts = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(parts) > 1 and len(parts[0].split()) < 30 and any(kw in parts[0].lower() for kw in ["prompt", "here", "draft", "we", "count"]):
        text = "\n\n".join(parts[1:])
        
    return text.strip('"\'').strip()


def _extract_json(text: str) -> dict:
    """Parse JSON from a Groq response, stripping markdown, conversational text, and <think> blocks.
    Finds the first '{' and last '}' to extract just the JSON object.
    """
    text = text.strip()
    
    # Strip <think>...</think> chain-of-thought block if present (common with Qwen models)
    text = strip_think_block(text)
    
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

async def _get_final_prompt_with_fallback(client, primary_model, timeout, messages, temperature, max_tokens) -> str:
    """Execute LLM call, parse JSON using multi-stage extraction."""
    for attempt in range(2):
        try:
            completion = await _chat_with_fallback(
                client,
                primary_model=primary_model,
                timeout=timeout,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raw_text = completion.choices[0].message.content
        except Exception as e:
            logger.warning("llm_call_failed", attempt=attempt, error=str(e))
            continue
            
        if not raw_text:
            continue
            
        raw_text = strip_think_block(raw_text).strip()
            
        # Stage 1: Attempt json.loads() on the raw response
        try:
            data = json.loads(raw_text)
            if "final_prompt" in data:
                logger.info("synthesize_prompt_done", extraction_method="json_direct")
                return data["final_prompt"].strip()
        except json.JSONDecodeError:
            pass

        # Stage 2: Attempt to locate a JSON object substring using regex
        try:
            match = re.search(r'\{[^{}]*"final_prompt"[^{}]*\}', raw_text, re.DOTALL | re.IGNORECASE)
            if match:
                data = json.loads(match.group(0))
                if "final_prompt" in data:
                    logger.info("synthesize_prompt_done", extraction_method="json_regex")
                    return data["final_prompt"].strip()
        except json.JSONDecodeError:
            pass

        # Stage 3: Attempt to extract the LAST quoted string (>= 40 chars)
        try:
            quotes = re.findall(r'"([^"]{40,})"', raw_text)
            if quotes:
                logger.info("synthesize_prompt_done", extraction_method="quote_fallback")
                return quotes[-1].strip()
        except Exception:
            pass

        logger.warning("json_extraction_failed_attempt", attempt=attempt, raw_text=raw_text)
        
    # Stage 4: If ALL THREE stages fail across all attempts
    logger.error("synthesize_prompt_failed", raw_text=raw_text if 'raw_text' in locals() else "No response")
    raise PromptSynthesisError("Prompt synthesis failed, please retry.")

SYSTEM_PROMPTS = {
    "image": 'You are a world-class image prompt engineer. Rewrite the user\'s prompt to be richly descriptive: include lighting, composition, style, color palette, and mood. Keep it under 200 words.\n\nOutput ONLY valid JSON: {"final_prompt": "your descriptive paragraph here"}. Do not include any explanation, reasoning, word counts, drafts, or text outside the JSON object. Your entire response must be parseable by json.loads().',
    "video": 'You are a world-class video prompt engineer. Rewrite the user\'s prompt to describe motion, pacing, camera movement, scene transitions, and visual atmosphere. Keep it under 150 words.\n\nOutput ONLY valid JSON: {"final_prompt": "your descriptive paragraph here"}. Do not include any explanation, reasoning, word counts, drafts, or text outside the JSON object. Your entire response must be parseable by json.loads().'
}

@async_retry(max_attempts=2, backoff_base=1.5)
async def enhance_prompt(raw: str, mode: Literal["image", "video"]) -> FinalPrompt:
    settings = get_settings()

    try:
        # Initialize Groq client. Uses GROQ_API_KEY from environment automatically if set
        client = AsyncGroq(api_key=settings.groq_api_key)
        
        system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["image"])
        
        enhanced_text = await _get_final_prompt_with_fallback(
            client=client,
            primary_model=settings.groq_model,
            timeout=settings.groq_timeout,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        
        return FinalPrompt(
            raw_prompt=raw,
            final_prompt=enhanced_text
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

Output ONLY valid JSON: {"final_prompt": "your descriptive paragraph here"}. Do not include any explanation, reasoning, word counts, drafts, or text outside the JSON object. Your entire response must be parseable by json.loads().
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
        return await _get_final_prompt_with_fallback(
            client=client,
            primary_model=settings.groq_model,
            timeout=settings.groq_timeout,
            messages=[
                {"role": "system", "content": SYNTHESIZE_SYSTEM_PROMPT},
                {"role": "user", "content": attribute_text},
            ],
            temperature=0.7,
            max_tokens=200,
        )

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

Output ONLY valid JSON: {"final_prompt": "your descriptive paragraph here"}. Do not include any explanation, reasoning, word counts, drafts, or text outside the JSON object. Your entire response must be parseable by json.loads().
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
        return await _get_final_prompt_with_fallback(
            client=client,
            primary_model=settings.groq_model,
            timeout=settings.groq_timeout,
            messages=[
                {"role": "system", "content": VIDEO_SYNTHESIZE_SYSTEM_PROMPT},
                {"role": "user", "content": attribute_text},
            ],
            temperature=0.7,
            max_tokens=250,
        )

    except asyncio.TimeoutError as e:
        logger.error("groq_video_synthesize_timeout", error=str(e))
        raise RetryableError("Video prompt synthesis timed out") from e
    except Exception as e:
        logger.error("groq_video_synthesize_error", error=str(e))
        raise RetryableError(f"Video prompt synthesis failed: {e}") from e
