"""
schemas.py — Pydantic request/response models for AI-Studio API.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


# ── Enums ─────────────────────────────────────────────────────────────────────

class GenerationMode(str, Enum):
    image = "image"
    video = "video"


class JobStatus(str, Enum):
    queued = "queued"
    generating = "generating"
    done = "done"
    failed = "failed"


# ── Requests ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str = Field(default="", max_length=2000, description="Raw user prompt (used for video; or image if no attributes provided)")
    mode: GenerationMode = GenerationMode.image
    # Structured image attributes (if provided, Groq synthesizes the final prompt)
    attributes: Optional["ImageAttributes"] = None
    # Structured video attributes (if provided, Groq synthesizes the final video prompt)
    video_attributes: Optional["VideoAttributes"] = None
    # Image-specific (optional)
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    num_inference_steps: int = Field(default=28, ge=1, le=50)
    # Video-specific (optional)
    aspect_ratio: str = Field(default="16:9", pattern=r"^\d+:\d+$")
    duration: int = Field(default=5, ge=1, le=20, description="Video duration in seconds")


# ── Internal job record ───────────────────────────────────────────────────────

class JobRecord(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: GenerationMode
    raw_prompt: str
    enhanced_prompt: Optional[str] = None
    status: JobStatus = JobStatus.queued
    provider: str = ""
    model: str = ""
    result_url: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: Optional[float] = None
    estimated_wait_seconds: Optional[int] = None  # for video jobs


class EnhancedPrompt(BaseModel):
    raw_prompt: str
    enhanced_prompt: str


# ── Image Attribute Analysis ──────────────────────────────────────────────────

class ImageAttributes(BaseModel):
    """5 fundamental visual attributes extracted from a user description by Groq."""
    subject: str = Field(..., description="Who or what is the main focus of the image")
    action: str = Field(..., description="What is happening — the pose, motion, or state")
    location: str = Field(..., description="The setting, environment, and time of day")
    composition: str = Field(..., description="Camera angle, framing, depth of field, lighting setup")
    style: str = Field(..., description="Overall aesthetic, art movement, color palette, mood")


class AnalyseRequest(BaseModel):
    """Request body for POST /analyse/image."""
    description: str = Field(..., min_length=1, max_length=2000, description="Raw user description")


class AnalyseResponse(BaseModel):
    """Response from POST /analyse/image — 5 attributes ready for user editing."""
    attributes: ImageAttributes
    raw_description: str


# ── Video Attribute Analysis ──────────────────────────────────────────────────

class VideoAttributes(BaseModel):
    """10 structured video attributes across 3 groups, extracted by Groq."""
    # GROUP: OVERALL
    subject:           str = Field(..., description="Who or what is the main focus of the video")
    action:            str = Field(..., description="What is happening — motion, behavior, narrative arc")
    scene:             str = Field(..., description="When and where — setting, environment, time of day, weather")
    style:             str = Field(..., description="Artistic filter / aesthetic (cinematic, documentary, animated, etc.)")
    temporal_elements: str = Field(..., description="Time-based changes: slow-mo, time-lapse, transitions, pacing rhythm")
    # GROUP: CAMERA
    camera_angles:    str = Field(..., description="Shot viewpoints — wide, close-up, bird's eye, dutch angle, etc.")
    camera_movements: str = Field(..., description="Dynamic experience — dolly, pan, handheld, steadicam, drone, etc.")
    lens_effects:     str = Field(..., description="How camera sees the world — bokeh, anamorphic, rack focus, distortion")
    # GROUP: AUDIO (informational — luma/ray-flash-2-720p is visual-only)
    dialogue:         str = Field(..., description="Spoken words or voice-over (used to guide visual mood; not rendered as audio)")
    sound_effects:    str = Field(..., description="Distinct sounds in the scene (used to guide visual energy; not rendered as audio)")


class VideoAnalyseRequest(BaseModel):
    """Request body for POST /analyse/video."""
    description: str = Field(..., min_length=1, max_length=2000, description="Raw user video description")


class VideoAnalyseResponse(BaseModel):
    """Response from POST /analyse/video — 10 attributes ready for user editing."""
    attributes: VideoAttributes
    raw_description: str


# ── Responses ─────────────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    """Returned immediately on job creation."""
    job_id: str
    status: JobStatus
    mode: GenerationMode
    raw_prompt: str
    message: str = "Job queued"
    estimated_wait_seconds: Optional[int] = None


class JobStatusResponse(BaseModel):
    """Returned by GET /jobs/{id}/status."""
    job_id: str
    status: JobStatus
    mode: GenerationMode
    raw_prompt: str
    enhanced_prompt: Optional[str] = None
    provider: str
    model: str
    retry_count: int
    created_at: datetime
    updated_at: datetime
    estimated_wait_seconds: Optional[int] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class JobResultResponse(BaseModel):
    """Returned by GET /jobs/{id}/result — only when status == done."""
    job_id: str
    status: JobStatus
    mode: GenerationMode
    raw_prompt: str
    enhanced_prompt: Optional[str] = None
    result_url: Optional[str] = None
    latency_ms: Optional[float] = None
    retry_count: int = 0
    error: Optional[str] = None
    error_type: Optional[str] = None
    cdn_expiry_note: str = "CDN links expire in approximately 24 hours."


class ServiceHealth(BaseModel):
    reachable: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    services: dict[str, ServiceHealth]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    error: str
    message: str
    job_id: Optional[str] = None
