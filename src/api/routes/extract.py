"""
Extract endpoint.
POST /api/v1/extract - Hook-driven snapshot & commit to repo.
"""
import logging
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional

from src.core.job_queue import get_job_queue, JobType
from src.core.config import get_settings
from src.api.models import JobAcceptedResponse
from src.workers.tasks import extract_task_sync

logger = logging.getLogger(__name__)

router = APIRouter()

settings = get_settings()


@router.post("/extract", response_model=JobAcceptedResponse, status_code=202)
async def extract_and_commit(
    file: Optional[UploadFile] = File(None, description="Excel file to extract"),
    origin_repo: Optional[str] = Form(None, description="Origin repository URL"),
    origin_path: Optional[str] = Form(None, description="Path in origin repo"),
    origin_commit: Optional[str] = Form(None, description="Origin commit SHA"),
    origin_commit_message: Optional[str] = Form(None, description="Commit message"),
    file_url: Optional[str] = Form(None, description="URL to fetch file from"),
    snapshot_repo_url: Optional[str] = Form(None, description="Override snapshot repo URL"),
    include_evaluated: bool = Form(False, description="Include evaluated values"),
):
    """
    Extract a workbook and commit snapshot to the snapshot repository.

    This endpoint is typically called by a Git hook or CI system when an Excel
    file is committed to a repository. It flattens the workbook and commits
    the snapshot to the configured snapshot repository.

    Either provide `file` (multipart upload) or `file_url` (server will fetch).

    Returns:
        - job_id: Unique identifier to poll for results
        - status: "accepted"

    Poll GET /api/v1/jobs/{job_id} for completion and results.
    """
    # Validate inputs
    if not file and not file_url:
        raise HTTPException(
            status_code=400,
            detail="Either 'file' or 'file_url' must be provided"
        )

    if file and file_url:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'file' or 'file_url', not both"
        )

    # Validate file size if file is provided
    if file:
        # Read file to check size
        file_content = await file.read()
        if len(file_content) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_BYTES} bytes"
            )
        # Reset file pointer
        await file.seek(0)

    # Submit job to queue
    queue = get_job_queue()

    job_id = queue.submit_job(
        job_type=JobType.EXTRACT,
        task_func=extract_task_sync,  # For multiprocessing backend
        file=file_content if file else None,
        filename=file.filename if file else None,
        origin_repo=origin_repo,
        origin_path=origin_path,
        origin_commit=origin_commit,
        origin_commit_message=origin_commit_message,
        file_url=file_url,
        snapshot_repo_url=snapshot_repo_url or settings.SNAPSHOT_REPO_URL,
        include_evaluated=include_evaluated,
    )

    logger.info(f"Extract job submitted: {job_id}")

    return JobAcceptedResponse(job_id=job_id)
