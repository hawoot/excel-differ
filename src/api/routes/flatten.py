"""
Flatten endpoint.
POST /api/v1/flatten - Flatten a single workbook to archive.
"""
import logging
from fastapi import APIRouter, File, UploadFile, Form, HTTPException

from src.core.job_queue import get_job_queue, JobType
from src.core.config import get_settings
from src.api.models import JobAcceptedResponse, ArchiveFormat

logger = logging.getLogger(__name__)

router = APIRouter()

settings = get_settings()


@router.post("/flatten", response_model=JobAcceptedResponse, status_code=202)
async def flatten_workbook(
    file: UploadFile = File(..., description="Excel file to flatten"),
    format: str = Form("zip", description="Archive format: zip or tar.gz"),
    include_evaluated: bool = Form(False, description="Include evaluated values"),
):
    """
    Flatten a single Excel workbook and return an archive.

    Upload an Excel file and receive a flattened snapshot as a downloadable
    archive (ZIP or TAR.GZ).

    Returns:
        - job_id: Unique identifier to poll for results
        - status: "accepted"

    Poll GET /api/v1/jobs/{job_id} for completion. Result will include:
        - archive_url: URL to download the archive
        - manifest: Manifest JSON
        - size_bytes: Archive size
    """
    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_BYTES} bytes"
        )

    # Validate format
    if format not in ["zip", "tar.gz"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Must be 'zip' or 'tar.gz'"
        )

    # Reset file pointer
    await file.seek(0)

    # Submit job
    queue = get_job_queue()

    logger.info("Flattening requested")

    job_id = queue.submit_job(
        job_type=JobType.FLATTEN,
        task_func=None,  # Will be implemented in tasks.py
        file=file_content,
        filename=file.filename,
        format=format,
        include_evaluated=include_evaluated,
    )

    logger.info(f"Flatten job submitted: {job_id}")

    return JobAcceptedResponse(job_id=job_id)
