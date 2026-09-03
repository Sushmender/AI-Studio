"""
jobs.py — Job polling endpoints.

GET /jobs            → paginated list of all jobs (newest first)
GET /jobs/{id}/status  → current job status + metadata
GET /jobs/{id}/result  → full result when done, error detail when failed
"""
from fastapi import APIRouter, HTTPException, Query

from backend.models.schemas import (
    JobResultResponse,
    JobStatus,
    JobStatusResponse,
)
from backend.services.job_store import job_store
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "",
    response_model=dict,
    summary="List recent jobs",
    response_description="Paginated list of job records, newest first",
)
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100, description="Max jobs to return (1–100)"),
    offset: int = Query(default=0, ge=0, description="Number of jobs to skip for pagination"),
):
    """
    Return all in-memory jobs sorted newest-first, with pagination.

    Useful for debugging, admin inspection, and the frontend gallery refresh.
    Jobs are purged automatically after **24 hours** by the background TTL task.

    **Response shape:** `{ jobs: [...], total: N, limit: N, offset: N }`
    """
    all_jobs = await job_store.list_jobs()
    # Sort newest first
    sorted_jobs = sorted(all_jobs, key=lambda j: j.created_at, reverse=True)
    total = len(sorted_jobs)
    page = sorted_jobs[offset : offset + limit]

    return {
        "jobs": [
            JobStatusResponse(
                job_id=j.job_id,
                status=j.status,
                mode=j.mode,
                raw_prompt=j.raw_prompt,
                enhanced_prompt=j.enhanced_prompt,
                provider=j.provider,
                model=j.model,
                retry_count=j.retry_count,
                created_at=j.created_at,
                updated_at=j.updated_at,
                estimated_wait_seconds=j.estimated_wait_seconds,
                error=j.error,
                error_type=j.error_type,
            )
            for j in page
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Poll job status",
    response_description="Current status, provider metadata, and optional error details",
)
async def get_job_status(job_id: str):
    """
    Return the current status of a job by its UUID.

    **Safe to call in a polling loop** — the endpoint reads from an in-memory
    dict and returns immediately.

    **Recommended polling intervals:**
    - Image jobs: every **2 seconds**
    - Video jobs: every **5 seconds** (typical generation time 2–5 min)

    **Returns 404** if the job has been purged (TTL 24 h) or never existed.
    """
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


@router.get(
    "/{job_id}/result",
    response_model=JobResultResponse,
    summary="Fetch job result",
    response_description="Full result including CDN URL when status is done; error detail when failed",
)
async def get_job_result(job_id: str):
    """
    Retrieve the final result of a completed job.

    - **HTTP 200** with `result_url` when `status == done`
    - **HTTP 200** with `error` / `error_type` when `status == failed`
    - **HTTP 202** (still in progress) while `status` is `queued` or `generating`
    - **HTTP 404** if the job does not exist or has expired (TTL 24 h)

    CDN links in `result_url` expire in approximately **24 hours**.
    """
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
        retry_count=record.retry_count,
        error=record.error,
        error_type=record.error_type,
    )
