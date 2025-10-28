"""
Snapshots endpoint.
GET /api/v1/snapshots/download - Download committed snapshot from repo.
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pathlib import Path
import zipfile
import io

from src.git_ops.snapshot_repo import get_snapshot_repo_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/snapshots/download")
async def download_snapshot(
    path: str = Query(..., description="Snapshot path in repository"),
):
    """
    Download a committed snapshot from the snapshot repository.

    Provide the snapshot path returned from an extract job to download
    the complete flattened snapshot as a ZIP archive.

    Args:
        path: Relative path to snapshot in repository (from extract job result)

    Returns:
        ZIP file containing the snapshot
    """
    repo_manager = get_snapshot_repo_manager()

    # Get snapshot directory
    snapshot_dir = repo_manager.get_snapshot(Path(path))

    if snapshot_dir is None or not snapshot_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Snapshot not found: {path}"
        )

    logger.info(f"Streaming snapshot download: {path}")

    # Create ZIP archive in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in snapshot_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(snapshot_dir)
                zipf.write(file_path, arcname)

    # Seek to beginning of buffer
    zip_buffer.seek(0)

    # Generate filename
    snapshot_name = snapshot_dir.name
    filename = f"{snapshot_name}.zip"

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
