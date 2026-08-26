"""
job_store.py — In-memory async job store.

Thread-safe via asyncio.Lock. State resets on server restart (POC-appropriate).
"""
import asyncio
from datetime import datetime
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


# Module-level singleton — imported by routes
job_store = JobStore()
