"""
jobs.py — Job polling endpoints.

GET /jobs/{id}/status  → current job status + metadata
GET /jobs/{id}/result  → full result when done, error detail when failed
"""
from fastapi import APIRouter, HTTPException

from backend.models.schemas import (
    JobResultResponse,
    JobStatus,
    JobStatusResponse,
)
from backend.services.job_store import job_store
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Poll job status. Safe to call repeatedly until status is done or failed."""
    record = await job_store.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return JobStatusResponse(
        job_id=record.job_id,
        status=record.status,
        mode=record.mode,
        raw_prompt=record.raw_prompt,
        enhanced_prompt=record.enhanced_prompt,
        provider=record.provider,
        model=record.model,
        retry_count=record.retry_count,
        created_at=record.created_at,
        updated_at=record.updated_at,
        estimated_wait_seconds=record.estimated_wait_seconds,
        error=record.error,
        error_type=record.error_type,
    )


@router.get("/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(job_id: str):
    """Get the final result. Returns 202 if still in progress, 200 if done/failed."""
    record = await job_store.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if record.status in (JobStatus.queued, JobStatus.generating):
        raise HTTPException(
            status_code=202,
            detail={
                "message": "Job still in progress",
                "status": record.status,
                "estimated_wait_seconds": record.estimated_wait_seconds,
            },
        )

    return JobResultResponse(
        job_id=record.job_id,
        status=record.status,
        mode=record.mode,
        raw_prompt=record.raw_prompt,
        enhanced_prompt=record.enhanced_prompt,
        result_url=record.result_url,
        latency_ms=record.latency_ms,
        error=record.error,
        error_type=record.error_type,
    )
