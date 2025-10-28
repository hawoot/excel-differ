"""
Job status endpoint.
GET /api/v1/jobs/{job_id} - Poll for job status and results.
"""
import logging
from fastapi import APIRouter, HTTPException, Path

from src.core.job_queue import get_job_queue, JobStatus as QueueJobStatus
from src.api.models import JobStatusResponse, JobStatus, JobType

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str = Path(..., description="Job ID to query"),
):
    """
    Get the status and results of a job.

    Poll this endpoint after submitting a job (extract, flatten, or compare)
    to check progress and retrieve results when complete.

    Returns:
        - status: queued, running, success, or failed
        - result: Job output (when status is success)
        - error: Error message (when status is failed)
    """
    queue = get_job_queue()

    job = queue.get_job_status(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Convert queue job status to API job status
    return JobStatusResponse(
        job_id=job.job_id,
        status=JobStatus(job.status.value),
        type=JobType(job.job_type.value),
        created_at=job.created_at.isoformat() if job.created_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        progress=job.progress,
        result=job.result,
        error=job.error,
    )
