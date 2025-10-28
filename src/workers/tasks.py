"""
Celery tasks for extract, flatten, and compare operations.
These are the actual worker functions that process jobs.
"""
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests

from src.workers.celery_app import celery_app
from src.core.storage import (
    create_temp_dir,
    cleanup_temp_dir,
    create_zip_archive,
    create_tar_archive,
    get_file_hash,
    get_snapshot_path,
)
from src.engine.flattener.workbook import WorkbookFlattener
from src.engine.differ.compare import SnapshotComparison
from src.engine.differ.diff_json import generate_json_diff
from src.git_ops.snapshot_repo import get_snapshot_repo_manager
from src.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


@celery_app.task(name="extract_task", bind=True)
def extract_task(
    self,
    file: Optional[bytes] = None,
    filename: Optional[str] = None,
    origin_repo: Optional[str] = None,
    origin_path: Optional[str] = None,
    origin_commit: Optional[str] = None,
    origin_commit_message: Optional[str] = None,
    file_url: Optional[str] = None,
    snapshot_repo_url: Optional[str] = None,
    include_evaluated: bool = False,
) -> Dict[str, Any]:
    """
    Extract task: flatten workbook and commit to snapshot repository.

    Args:
        file: File content (bytes)
        filename: Original filename
        origin_repo: Origin repository URL
        origin_path: Path in origin repo
        origin_commit: Origin commit SHA
        origin_commit_message: Origin commit message
        file_url: URL to fetch file from
        snapshot_repo_url: Snapshot repo URL
        include_evaluated: Include evaluated values

    Returns:
        Dict with commit_sha, snapshot_path, manifest
    """
    temp_dir = None

    try:
        logger.info(f"Extract task started: {self.request.id}")

        # Create temp directory
        temp_dir = create_temp_dir(prefix="extract")

        # Get file content
        if file:
            # File was uploaded
            input_file = temp_dir / (filename or "workbook.xlsx")
            with open(input_file, "wb") as f:
                f.write(file)

        elif file_url:
            # Fetch file from URL
            logger.info(f"Fetching file from: {file_url}")
            response = requests.get(file_url, timeout=60)
            response.raise_for_status()

            input_file = temp_dir / (filename or "workbook.xlsx")
            with open(input_file, "wb") as f:
                f.write(response.content)

        else:
            raise ValueError("Either file or file_url must be provided")

        # Flatten workbook
        logger.info("Flattening workbook...")
        flattener = WorkbookFlattener(include_evaluated=include_evaluated)

        result = flattener.flatten(
            input_file=input_file,
            output_dir=temp_dir / "output",
            origin_repo=origin_repo,
            origin_path=origin_path,
            origin_commit=origin_commit,
            origin_commit_message=origin_commit_message,
        )

        snapshot_dir = result["snapshot_dir"]
        manifest = result["manifest"]

        # Calculate snapshot path for repo
        file_hash = get_file_hash(input_file)
        timestamp = datetime.now(timezone.utc)

        repo_snapshot_path = get_snapshot_path(
            origin_repo=origin_repo,
            origin_path=origin_path,
            filename=input_file.name,
            timestamp=timestamp,
            file_hash=file_hash,
        )

        # Commit to snapshot repository
        logger.info(f"Committing to snapshot repository at: {repo_snapshot_path}")
        repo_manager = get_snapshot_repo_manager()

        commit_sha = repo_manager.commit_snapshot(
            snapshot_dir=snapshot_dir,
            original_file=input_file,
            snapshot_path=repo_snapshot_path,
            commit_message=origin_commit_message,
            metadata={
                "origin_repo": origin_repo,
                "origin_path": origin_path,
                "origin_commit": origin_commit,
                "origin_commit_message": origin_commit_message,
            },
        )

        logger.info(f"Extract task completed: commit {commit_sha}")

        return {
            "commit_sha": commit_sha,
            "snapshot_path": str(repo_snapshot_path),
            "manifest": manifest.to_dict(),
        }

    except Exception as e:
        logger.exception(f"Extract task failed: {e}")
        raise

    finally:
        if temp_dir:
            cleanup_temp_dir(temp_dir)


# @celery_app.task(name="flatten_task", bind=True)
def flatten_task(
    self,
    file: bytes,
    filename: str,
    format: str = "zip",
    include_evaluated: bool = False,
) -> Dict[str, Any]:
    """
    Flatten task: flatten workbook and create archive.

    Args:
        file: File content (bytes)
        filename: Original filename
        format: Archive format (zip or tar.gz)
        include_evaluated: Include evaluated values

    Returns:
        Dict with archive_url, manifest, size_bytes
    """
    temp_dir = None

    try:
        logger.info(f"Flatten task started: {self.request.id}")

        # Create temp directory
        temp_dir = create_temp_dir(prefix="flatten")

        # Write input file
        input_file = temp_dir / filename
        with open(input_file, "wb") as f:
            f.write(file)

        # Flatten workbook
        logger.info("Flattening workbook...")
        flattener = WorkbookFlattener(include_evaluated=include_evaluated)

        result = flattener.flatten(
            input_file=input_file,
            output_dir=temp_dir / "output",
        )

        snapshot_dir = result["snapshot_dir"]
        manifest = result["manifest"]

        # Create archive
        archive_name = f"{snapshot_dir.name}.{format.replace('.', '')}"
        archive_path = temp_dir / archive_name

        if format == "zip":
            create_zip_archive(snapshot_dir, archive_path)
        elif format == "tar.gz":
            create_tar_archive(snapshot_dir, archive_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Store archive for download
        # For now, we'll return the archive path
        # In production, upload to object storage (S3, etc.)
        archive_size = archive_path.stat().st_size

        logger.info(f"Flatten task completed: {archive_path} ({archive_size} bytes)")

        return {
            "archive_url": f"/downloads/{archive_name}",  # Placeholder
            "manifest": manifest.to_dict(),
            "size_bytes": archive_size,
        }

    except Exception as e:
        logger.exception(f"Flatten task failed: {e}")
        raise

    finally:
        # Note: Don't cleanup yet - archive needs to be downloaded
        # Implement TTL-based cleanup separately
        pass


@celery_app.task(name="compare_task", bind=True)
def compare_task(
    self,
    file_a: Optional[bytes] = None,
    filename_a: Optional[str] = None,
    file_b: Optional[bytes] = None,
    filename_b: Optional[str] = None,
    snapshot_path_a: Optional[str] = None,
    snapshot_path_b: Optional[str] = None,
    output: str = "both",
    include_evaluated: bool = False,
    diff_context: int = 3,
) -> Dict[str, Any]:
    """
    Compare task: compare two workbooks or snapshots.

    Args:
        file_a: First file content
        filename_a: First filename
        file_b: Second file content
        filename_b: Second filename
        snapshot_path_a: Path to first snapshot in repo
        snapshot_path_b: Path to second snapshot in repo
        output: Output format (both, json, text)
        include_evaluated: Include evaluated values
        diff_context: Context lines for unified diff

    Returns:
        Dict with diff_json, diff_unified, summary
    """
    temp_dir = None

    try:
        logger.info(f"Compare task started: {self.request.id}")

        # Create temp directory
        temp_dir = create_temp_dir(prefix="compare")

        # Determine snapshot directories
        if file_a and file_b:
            # Flatten both files
            logger.info("Flattening both files...")

            # Flatten file A
            input_a = temp_dir / (filename_a or "file_a.xlsx")
            with open(input_a, "wb") as f:
                f.write(file_a)

            flattener = WorkbookFlattener(include_evaluated=include_evaluated)
            result_a = flattener.flatten(input_a, temp_dir / "output_a")
            snapshot_a = result_a["snapshot_dir"]

            # Flatten file B
            input_b = temp_dir / (filename_b or "file_b.xlsx")
            with open(input_b, "wb") as f:
                f.write(file_b)

            result_b = flattener.flatten(input_b, temp_dir / "output_b")
            snapshot_b = result_b["snapshot_dir"]

        elif snapshot_path_a and snapshot_path_b:
            # Use existing snapshots from repo
            logger.info(f"Using existing snapshots: {snapshot_path_a}, {snapshot_path_b}")

            repo_manager = get_snapshot_repo_manager()

            snapshot_a = repo_manager.get_snapshot(Path(snapshot_path_a))
            snapshot_b = repo_manager.get_snapshot(Path(snapshot_path_b))

            if not snapshot_a or not snapshot_b:
                raise ValueError("One or both snapshot paths not found in repository")

        else:
            raise ValueError("Either provide files or snapshot paths")

        # Compare snapshots
        logger.info("Comparing snapshots...")
        comparison = SnapshotComparison(snapshot_a, snapshot_b)

        # Generate JSON diff
        result = generate_json_diff(comparison)

        diff_json = result["diff_json"]
        summary = result["summary"]

        # Generate unified diff if requested
        diff_unified = None
        if output in ["both", "text"]:
            diff_unified = comparison.get_full_unified_diff(context_lines=diff_context)

        logger.info(f"Compare task completed: {len(diff_json)} changes detected")

        return_data = {
            "summary": summary,
        }

        if output in ["both", "json"]:
            return_data["diff_json"] = diff_json

        if output in ["both", "text"]:
            return_data["diff_unified"] = diff_unified

        return return_data

    except Exception as e:
        logger.exception(f"Compare task failed: {e}")
        raise

    finally:
        if temp_dir:
            cleanup_temp_dir(temp_dir)


# For multiprocessing backend compatibility
# These functions can be called directly (not via Celery)

def extract_task_sync(
    file: Optional[bytes] = None,
    filename: Optional[str] = None,
    origin_repo: Optional[str] = None,
    origin_path: Optional[str] = None,
    origin_commit: Optional[str] = None,
    origin_commit_message: Optional[str] = None,
    file_url: Optional[str] = None,
    snapshot_repo_url: Optional[str] = None,
    include_evaluated: bool = False,
) -> Dict[str, Any]:
    """Synchronous version of extract_task for multiprocessing backend."""
    temp_dir = None

    try:
        logger.info("Extract task started (sync mode)")

        # Create temp directory
        temp_dir = create_temp_dir(prefix="extract")

        # Get file content
        if file:
            # File was uploaded
            input_file = temp_dir / (filename or "workbook.xlsx")
            with open(input_file, "wb") as f:
                f.write(file)

        elif file_url:
            # Fetch file from URL
            logger.info(f"Fetching file from: {file_url}")
            response = requests.get(file_url, timeout=60)
            response.raise_for_status()

            input_file = temp_dir / (filename or "workbook.xlsx")
            with open(input_file, "wb") as f:
                f.write(response.content)

        else:
            raise ValueError("Either file or file_url must be provided")

        # Flatten workbook
        logger.info("Flattening workbook...")
        flattener = WorkbookFlattener(include_evaluated=include_evaluated)

        result = flattener.flatten(
            input_file=input_file,
            output_dir=temp_dir / "output",
            origin_repo=origin_repo,
            origin_path=origin_path,
            origin_commit=origin_commit,
            origin_commit_message=origin_commit_message,
        )

        snapshot_dir = result["snapshot_dir"]
        manifest = result["manifest"]

        # Calculate snapshot path for repo
        file_hash = get_file_hash(input_file)
        timestamp = datetime.now(timezone.utc)

        repo_snapshot_path = get_snapshot_path(
            origin_repo=origin_repo,
            origin_path=origin_path,
            filename=input_file.name,
            timestamp=timestamp,
            file_hash=file_hash,
        )

        # Commit to snapshot repository
        logger.info(f"Committing to snapshot repository at: {repo_snapshot_path}")
        repo_manager = get_snapshot_repo_manager()

        commit_sha = repo_manager.commit_snapshot(
            snapshot_dir=snapshot_dir,
            original_file=input_file,
            snapshot_path=repo_snapshot_path,
            commit_message=origin_commit_message,
            metadata={
                "origin_repo": origin_repo,
                "origin_path": origin_path,
                "origin_commit": origin_commit,
                "origin_commit_message": origin_commit_message,
            },
        )

        logger.info(f"Extract task completed: commit {commit_sha}")

        return {
            "commit_sha": commit_sha,
            "snapshot_path": str(repo_snapshot_path),
            "manifest": manifest.to_dict(),
        }

    except Exception as e:
        logger.exception(f"Extract task failed: {e}")
        raise

    finally:
        if temp_dir:
            cleanup_temp_dir(temp_dir)


def flatten_task_sync(
    file: bytes,
    filename: str,
    format: str = "zip",
    include_evaluated: bool = False,
) -> Dict[str, Any]:
    """Synchronous version of flatten_task for multiprocessing backend."""
    temp_dir = None

    try:
        logger.info("Flatten task started (sync mode)")

        # Create temp directory
        temp_dir = create_temp_dir(prefix="flatten")

        # Write input file
        input_file = temp_dir / filename
        with open(input_file, "wb") as f:
            f.write(file)

        # Flatten workbook
        logger.info("Flattening workbook...")
        flattener = WorkbookFlattener(include_evaluated=include_evaluated)

        result = flattener.flatten(
            input_file=input_file,
            output_dir=temp_dir / "output",
        )

        snapshot_dir = result["snapshot_dir"]
        manifest = result["manifest"]

        # Create archive
        archive_name = f"{snapshot_dir.name}.{format.replace('.', '')}"
        archive_path = temp_dir / archive_name

        if format == "zip":
            create_zip_archive(snapshot_dir, archive_path)
        elif format == "tar.gz":
            create_tar_archive(snapshot_dir, archive_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Store archive for download
        archive_size = archive_path.stat().st_size

        logger.info(f"Flatten task completed: {archive_path} ({archive_size} bytes)")

        return {
            "archive_url": f"/downloads/{archive_name}",
            "manifest": manifest.to_dict(),
            "size_bytes": archive_size,
        }

    except Exception as e:
        logger.exception(f"Flatten task failed: {e}")
        raise

    finally:
        # Note: Don't cleanup yet - archive needs to be downloaded
        pass


def compare_task_sync(
    file_a: Optional[bytes] = None,
    filename_a: Optional[str] = None,
    file_b: Optional[bytes] = None,
    filename_b: Optional[str] = None,
    snapshot_path_a: Optional[str] = None,
    snapshot_path_b: Optional[str] = None,
    output: str = "both",
    include_evaluated: bool = False,
    diff_context: int = 3,
) -> Dict[str, Any]:
    """Synchronous version of compare_task for multiprocessing backend."""
    temp_dir = None

    try:
        logger.info("Compare task started (sync mode)")

        # Create temp directory
        temp_dir = create_temp_dir(prefix="compare")

        # Determine snapshot directories
        if file_a and file_b:
            # Flatten both files
            logger.info("Flattening both files...")

            # Flatten file A
            input_a = temp_dir / (filename_a or "file_a.xlsx")
            with open(input_a, "wb") as f:
                f.write(file_a)

            flattener = WorkbookFlattener(include_evaluated=include_evaluated)
            result_a = flattener.flatten(input_a, temp_dir / "output_a")
            snapshot_a = result_a["snapshot_dir"]

            # Flatten file B
            input_b = temp_dir / (filename_b or "file_b.xlsx")
            with open(input_b, "wb") as f:
                f.write(file_b)

            result_b = flattener.flatten(input_b, temp_dir / "output_b")
            snapshot_b = result_b["snapshot_dir"]

        elif snapshot_path_a and snapshot_path_b:
            # Use existing snapshots from repo
            logger.info(f"Using existing snapshots: {snapshot_path_a}, {snapshot_path_b}")

            repo_manager = get_snapshot_repo_manager()

            snapshot_a = repo_manager.get_snapshot(Path(snapshot_path_a))
            snapshot_b = repo_manager.get_snapshot(Path(snapshot_path_b))

            if not snapshot_a or not snapshot_b:
                raise ValueError("One or both snapshot paths not found in repository")

        else:
            raise ValueError("Either provide files or snapshot paths")

        # Compare snapshots
        logger.info("Comparing snapshots...")
        comparison = SnapshotComparison(snapshot_a, snapshot_b)

        # Generate JSON diff
        result = generate_json_diff(comparison)

        diff_json = result["diff_json"]
        summary = result["summary"]

        # Generate unified diff if requested
        diff_unified = None
        if output in ["both", "text"]:
            diff_unified = comparison.get_full_unified_diff(context_lines=diff_context)

        logger.info(f"Compare task completed: {len(diff_json)} changes detected")

        return_data = {
            "summary": summary,
        }

        if output in ["both", "json"]:
            return_data["diff_json"] = diff_json

        if output in ["both", "text"]:
            return_data["diff_unified"] = diff_unified

        return return_data

    except Exception as e:
        logger.exception(f"Compare task failed: {e}")
        raise

    finally:
        if temp_dir:
            cleanup_temp_dir(temp_dir)
