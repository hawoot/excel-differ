"""
Compare endpoint.
POST /api/v1/compare - Compare two workbooks or snapshots.
"""
import logging
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional

from src.core.job_queue import get_job_queue, JobType
from src.core.config import get_settings
from src.api.models import JobAcceptedResponse
from src.workers.tasks import compare_task_sync

logger = logging.getLogger(__name__)

router = APIRouter()

settings = get_settings()


@router.post("/compare", response_model=JobAcceptedResponse, status_code=202)
async def compare_workbooks(
    file_a: Optional[UploadFile] = File(None, description="First Excel file"),
    file_b: Optional[UploadFile] = File(None, description="Second Excel file"),
    snapshot_path_a: Optional[str] = Form(None, description="Path to first snapshot in repo"),
    snapshot_path_b: Optional[str] = Form(None, description="Path to second snapshot in repo"),
    output: str = Form("both", description="Output format: both, json, or text"),
    include_evaluated: bool = Form(False, description="Include evaluated values"),
    diff_context: int = Form(3, description="Context lines for unified diff (0-10)"),
):
    """
    Compare two Excel workbooks or snapshots.

    You can either:
    1. Upload two files (file_a and file_b)
    2. Reference two existing snapshots (snapshot_path_a and snapshot_path_b)

    Returns:
        - job_id: Unique identifier to poll for results
        - status: "accepted"

    Poll GET /api/v1/jobs/{job_id} for completion. Result will include:
        - diff_json: Structured diff array with typed change objects
        - diff_unified: Unified text diff (if output includes 'text')
        - summary: Summary statistics
    """
    # Validate inputs
    using_files = file_a and file_b
    using_snapshots = snapshot_path_a and snapshot_path_b

    if not using_files and not using_snapshots:
        raise HTTPException(
            status_code=400,
            detail="Either provide (file_a and file_b) or (snapshot_path_a and snapshot_path_b)"
        )

    if using_files and using_snapshots:
        raise HTTPException(
            status_code=400,
            detail="Provide either files or snapshot paths, not both"
        )

    # Validate output format
    if output not in ["both", "json", "text"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid output format. Must be 'both', 'json', or 'text'"
        )

    # Validate diff_context
    if diff_context < 0 or diff_context > 10:
        raise HTTPException(
            status_code=400,
            detail="diff_context must be between 0 and 10"
        )

    # If using files, validate size
    file_a_content = None
    file_b_content = None

    if using_files:
        file_a_content = await file_a.read()
        file_b_content = await file_b.read()

        if len(file_a_content) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"file_a too large. Maximum size: {settings.MAX_UPLOAD_BYTES} bytes"
            )

        if len(file_b_content) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"file_b too large. Maximum size: {settings.MAX_UPLOAD_BYTES} bytes"
            )

    # Submit job
    queue = get_job_queue()

    job_id = queue.submit_job(
        job_type=JobType.COMPARE,
        task_func=compare_task_sync,  # For multiprocessing backend
        file_a=file_a_content,
        filename_a=file_a.filename if file_a else None,
        file_b=file_b_content,
        filename_b=file_b.filename if file_b else None,
        snapshot_path_a=snapshot_path_a,
        snapshot_path_b=snapshot_path_b,
        output=output,
        include_evaluated=include_evaluated,
        diff_context=diff_context,
    )

    logger.info(f"Compare job submitted: {job_id}")

    return JobAcceptedResponse(job_id=job_id)
