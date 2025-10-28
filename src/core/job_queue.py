"""
Job queue abstraction layer.
Supports both Celery (with Redis) and multiprocessing backends.
Switch between them using QUEUE_BACKEND config.
"""
import uuid
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
import logging

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enum."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class JobType(str, Enum):
    """Job type enum."""
    EXTRACT = "extract"
    FLATTEN = "flatten"
    COMPARE = "compare"


class Job:
    """Job data structure."""

    def __init__(
        self,
        job_id: str,
        job_type: JobType,
        status: JobStatus = JobStatus.QUEUED,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        progress: int = 0,
    ):
        self.job_id = job_id
        self.job_type = job_type
        self.status = status
        self.result = result
        self.error = error
        self.progress = progress
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "job_id": self.job_id,
            "type": self.job_type.value,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class JobQueueBackend(ABC):
    """Abstract base class for job queue backends."""

    @abstractmethod
    def submit_job(
        self, job_type: JobType, task_func: Callable, **kwargs
    ) -> str:
        """
        Submit a job to the queue.

        Args:
            job_type: Type of job (extract, flatten, compare)
            task_func: The function to execute
            **kwargs: Arguments to pass to the task function

        Returns:
            job_id: Unique job identifier
        """
        pass

    @abstractmethod
    def get_job_status(self, job_id: str) -> Optional[Job]:
        """
        Get the status and result of a job.

        Args:
            job_id: Job identifier

        Returns:
            Job object or None if not found
        """
        pass

    @abstractmethod
    def cleanup_old_jobs(self, ttl_seconds: int) -> int:
        """
        Clean up jobs older than TTL.

        Args:
            ttl_seconds: Time to live in seconds

        Returns:
            Number of jobs cleaned up
        """
        pass


class MultiprocessingBackend(JobQueueBackend):
    """
    Simple thread-based job queue.
    Stores job metadata in JSON files.
    Good for environments without Redis.
    Note: Uses threads instead of processes for simpler serialization.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        settings = get_settings()
        self.jobs_dir = settings.TEMP_STORAGE_PATH / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"MultiprocessingBackend initialized with {max_workers} thread workers")

    def _get_job_file(self, job_id: str) -> Path:
        """Get the path to a job's metadata file."""
        return self.jobs_dir / f"{job_id}.json"

    def _save_job(self, job: Job) -> None:
        """Save job metadata to disk."""
        job_file = self._get_job_file(job.job_id)
        with open(job_file, "w") as f:
            json.dump(job.to_dict(), f, indent=2)

    def _load_job(self, job_id: str) -> Optional[Job]:
        """Load job metadata from disk."""
        job_file = self._get_job_file(job_id)
        if not job_file.exists():
            return None

        with open(job_file, "r") as f:
            data = json.load(f)

        job = Job(
            job_id=data["job_id"],
            job_type=JobType(data["type"]),
            status=JobStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            progress=data.get("progress", 0),
        )

        if data.get("created_at"):
            job.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            job.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            job.completed_at = datetime.fromisoformat(data["completed_at"])

        return job

    def _task_wrapper(self, job_id: str, task_func: Callable, **kwargs) -> None:
        """
        Wrapper that executes the task and updates job status.
        This runs in a separate thread.
        """
        logger.info(f"Task wrapper started for job {job_id}")
        try:
            # Update status to RUNNING
            job = self._load_job(job_id)
            if job:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                self._save_job(job)
                logger.info(f"Job {job_id} status updated to RUNNING")

            # Execute the task
            logger.info(f"Executing task for job {job_id}")
            result = task_func(**kwargs)
            logger.info(f"Task completed for job {job_id}")

            # Update status to SUCCESS
            job = self._load_job(job_id)
            if job:
                job.status = JobStatus.SUCCESS
                job.result = result
                job.completed_at = datetime.now(timezone.utc)
                self._save_job(job)
                logger.info(f"Job {job_id} status updated to SUCCESS")

        except Exception as e:
            logger.exception(f"Task failed for job {job_id}: {e}")
            # Update status to FAILED
            job = self._load_job(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.now(timezone.utc)
                self._save_job(job)
                logger.error(f"Job {job_id} status updated to FAILED: {e}")

    def submit_job(
        self, job_type: JobType, task_func: Callable, **kwargs
    ) -> str:
        """Submit a job to the multiprocessing executor."""
        job_id = str(uuid.uuid4())

        if task_func is None:
            raise ValueError("task_func is required for multiprocessing backend")

        # Create initial job metadata
        job = Job(job_id=job_id, job_type=job_type, status=JobStatus.QUEUED)
        self._save_job(job)

        # Submit to executor
        self.executor.submit(self._task_wrapper, job_id, task_func, **kwargs)

        logger.info(f"Job {job_id} ({job_type.value}) submitted to multiprocessing queue")
        return job_id

    def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get job status from disk."""
        return self._load_job(job_id)

    def cleanup_old_jobs(self, ttl_seconds: int) -> int:
        """Clean up old job files."""
        count = 0
        cutoff_time = time.time() - ttl_seconds

        for job_file in self.jobs_dir.glob("*.json"):
            if job_file.stat().st_mtime < cutoff_time:
                job_file.unlink()
                count += 1

        logger.info(f"Cleaned up {count} old jobs")
        return count


class CeleryBackend(JobQueueBackend):
    """
    Celery-based job queue with Redis.
    More robust for production environments.
    """

    def __init__(self):
        # Import celery only when needed
        try:
            from src.workers.celery_app import celery_app
            self.celery_app = celery_app
            logger.info("CeleryBackend initialized")
        except ImportError as e:
            logger.error(f"Failed to import Celery: {e}")
            raise RuntimeError(
                "Celery is not available. Install with: pip install celery redis"
            )

    def submit_job(
        self, job_type: JobType, task_func: Callable, **kwargs
    ) -> str:
        """Submit a job to Celery."""
        job_id = str(uuid.uuid4())

        # Import tasks dynamically
        from src.workers import tasks

        # Map job type to Celery task
        task_map = {
            JobType.EXTRACT: tasks.extract_task,
            JobType.FLATTEN: tasks.flatten_task,
            JobType.COMPARE: tasks.compare_task,
        }

        celery_task = task_map.get(job_type)
        if not celery_task:
            raise ValueError(f"Unknown job type: {job_type}")

        # Submit task with custom job_id
        celery_task.apply_async(kwargs=kwargs, task_id=job_id)

        logger.info(f"Job {job_id} ({job_type.value}) submitted to Celery")
        return job_id

    def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get job status from Celery."""
        from celery.result import AsyncResult

        result = AsyncResult(job_id, app=self.celery_app)

        # Map Celery states to our JobStatus
        status_map = {
            "PENDING": JobStatus.QUEUED,
            "STARTED": JobStatus.RUNNING,
            "SUCCESS": JobStatus.SUCCESS,
            "FAILURE": JobStatus.FAILED,
            "RETRY": JobStatus.RUNNING,
            "REVOKED": JobStatus.FAILED,
        }

        status = status_map.get(result.state, JobStatus.QUEUED)

        # Extract job type from result metadata if available
        job_type = JobType.EXTRACT  # Default
        if hasattr(result, 'name') and result.name:
            if 'extract' in result.name:
                job_type = JobType.EXTRACT
            elif 'flatten' in result.name:
                job_type = JobType.FLATTEN
            elif 'compare' in result.name:
                job_type = JobType.COMPARE

        job = Job(
            job_id=job_id,
            job_type=job_type,
            status=status,
        )

        if status == JobStatus.SUCCESS:
            job.result = result.result
            job.completed_at = datetime.now(timezone.utc)
        elif status == JobStatus.FAILED:
            job.error = str(result.result) if result.result else "Unknown error"
            job.completed_at = datetime.now(timezone.utc)
        elif status == JobStatus.RUNNING:
            job.started_at = datetime.now(timezone.utc)

        return job

    def cleanup_old_jobs(self, ttl_seconds: int) -> int:
        """
        Clean up old jobs from Celery.
        Note: Celery has its own result expiry settings.
        """
        # Celery automatically expires results based on CELERY_RESULT_EXPIRES
        # This is a no-op for Celery backend
        logger.info("Celery backend handles its own result cleanup via CELERY_RESULT_EXPIRES")
        return 0


# Factory function to get the appropriate backend
_backend_instance: Optional[JobQueueBackend] = None


def get_job_queue() -> JobQueueBackend:
    """
    Get the configured job queue backend (singleton).

    Returns:
        JobQueueBackend instance (Celery or Multiprocessing)
    """
    global _backend_instance

    if _backend_instance is not None:
        return _backend_instance

    settings = get_settings()

    if settings.QUEUE_BACKEND == "celery":
        _backend_instance = CeleryBackend()
    elif settings.QUEUE_BACKEND == "multiprocessing":
        _backend_instance = MultiprocessingBackend(max_workers=settings.WORKER_CONCURRENCY)
    else:
        raise ValueError(f"Unknown QUEUE_BACKEND: {settings.QUEUE_BACKEND}")

    return _backend_instance
