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
    prompt: str = Field(..., min_length=1, max_length=2000, description="Raw user prompt")
    mode: GenerationMode = GenerationMode.image
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
