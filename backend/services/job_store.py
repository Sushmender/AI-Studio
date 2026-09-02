"""
job_store.py — In-memory async job store.

Thread-safe via asyncio.Lock. State resets on server restart (POC-appropriate).
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from backend.models.schemas import JobRecord, JobStatus
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class JobStore:
    def __init__(self) -> None:
        self._store: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, record: JobRecord) -> JobRecord:
        async with self._lock:
            self._store[record.job_id] = record
        logger.info("job_created", job_id=record.job_id, mode=record.mode, status=record.status)
        return record

    async def update_job(self, job_id: str, **fields) -> Optional[JobRecord]:
        async with self._lock:
            record = self._store.get(job_id)
            if record is None:
                logger.warning("job_update_not_found", job_id=job_id)
                return None
            updated = record.model_copy(
                update={**fields, "updated_at": datetime.utcnow()}
            )
            self._store[job_id] = updated
        return updated

    async def get_job(self, job_id: str) -> Optional[JobRecord]:
        async with self._lock:
            return self._store.get(job_id)

    async def list_jobs(self) -> list[JobRecord]:
        async with self._lock:
            return list(self._store.values())

    async def purge_expired(self, ttl_hours: int = 24) -> int:
        """
        Remove jobs whose updated_at is older than ttl_hours.
        Returns the count of purged jobs.
        Skips jobs that are still queued/generating — they may still be active.
        """
        cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
        purged = 0
        async with self._lock:
            expired_ids = [
                job_id
                for job_id, record in self._store.items()
                if record.updated_at < cutoff
                and record.status not in (JobStatus.queued, JobStatus.generating)
            ]
            for job_id in expired_ids:
                del self._store[job_id]
                purged += 1
        if purged:
            logger.info("jobs_purged", count=purged, ttl_hours=ttl_hours)
        return purged


# Module-level singleton — imported by routes
job_store = JobStore()
