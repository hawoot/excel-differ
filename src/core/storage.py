"""
Storage utilities for temporary files, archives, and cleanup.
"""
import shutil
import hashlib
import time
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
import logging

from src.core.config import get_settings

logger = logging.getLogger(__name__)


def get_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Calculate hash of a file.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5, etc.)

    Returns:
        Hex digest of file hash
    """
    hasher = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_temp_dir(prefix: str = "job") -> Path:
    """
    Create a temporary directory for job processing.

    Args:
        prefix: Prefix for directory name

    Returns:
        Path to created directory
    """
    settings = get_settings()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    temp_dir = settings.TEMP_STORAGE_PATH / f"{prefix}_{timestamp}_{id(object())}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Created temp directory: {temp_dir}")
    return temp_dir


def create_zip_archive(source_dir: Path, output_path: Path) -> Path:
    """
    Create a ZIP archive from a directory.

    Args:
        source_dir: Directory to archive
        output_path: Path for output ZIP file

    Returns:
        Path to created archive
    """
    logger.info(f"Creating ZIP archive: {output_path}")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(source_dir)
                zipf.write(file_path, arcname)

    logger.info(f"ZIP archive created: {output_path} ({output_path.stat().st_size} bytes)")
    return output_path


def create_tar_archive(source_dir: Path, output_path: Path) -> Path:
    """
    Create a TAR.GZ archive from a directory.

    Args:
        source_dir: Directory to archive
        output_path: Path for output TAR.GZ file

    Returns:
        Path to created archive
    """
    logger.info(f"Creating TAR.GZ archive: {output_path}")

    with tarfile.open(output_path, "w:gz") as tarf:
        tarf.add(source_dir, arcname=source_dir.name)

    logger.info(f"TAR.GZ archive created: {output_path} ({output_path.stat().st_size} bytes)")
    return output_path


def extract_zip_archive(archive_path: Path, output_dir: Path) -> Path:
    """
    Extract a ZIP archive.

    Args:
        archive_path: Path to ZIP file
        output_dir: Directory to extract to

    Returns:
        Path to extraction directory
    """
    logger.info(f"Extracting ZIP archive: {archive_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "r") as zipf:
        zipf.extractall(output_dir)

    logger.info(f"ZIP archive extracted to: {output_dir}")
    return output_dir


def cleanup_temp_dir(temp_dir: Path) -> None:
    """
    Remove a temporary directory and all its contents.

    Args:
        temp_dir: Directory to remove
    """
    if temp_dir.exists() and temp_dir.is_dir():
        try:
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")


def cleanup_old_files(directory: Path, ttl_seconds: int, pattern: str = "*") -> int:
    """
    Clean up files older than TTL in a directory.

    Args:
        directory: Directory to clean
        ttl_seconds: Time to live in seconds
        pattern: Glob pattern for files to consider

    Returns:
        Number of files deleted
    """
    if not directory.exists():
        return 0

    count = 0
    cutoff_time = time.time() - ttl_seconds

    for file_path in directory.glob(pattern):
        if file_path.is_file():
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    count += 1
                    logger.debug(f"Deleted old file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete old file {file_path}: {e}")

    if count > 0:
        logger.info(f"Cleaned up {count} old files from {directory}")

    return count


def cleanup_old_directories(directory: Path, ttl_seconds: int) -> int:
    """
    Clean up directories older than TTL.

    Args:
        directory: Parent directory to clean
        ttl_seconds: Time to live in seconds

    Returns:
        Number of directories deleted
    """
    if not directory.exists():
        return 0

    count = 0
    cutoff_time = time.time() - ttl_seconds

    for subdir in directory.iterdir():
        if subdir.is_dir():
            try:
                if subdir.stat().st_mtime < cutoff_time:
                    shutil.rmtree(subdir)
                    count += 1
                    logger.debug(f"Deleted old directory: {subdir}")
            except Exception as e:
                logger.warning(f"Failed to delete old directory {subdir}: {e}")

    if count > 0:
        logger.info(f"Cleaned up {count} old directories from {directory}")

    return count


def save_uploaded_file(uploaded_file, destination: Path) -> Path:
    """
    Save an uploaded file to disk.

    Args:
        uploaded_file: FastAPI UploadFile object
        destination: Path to save file

    Returns:
        Path to saved file
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    with open(destination, "wb") as f:
        # Read in chunks to handle large files
        while chunk := uploaded_file.file.read(65536):
            f.write(chunk)

    logger.info(f"Saved uploaded file to: {destination}")
    return destination


def get_snapshot_path(
    origin_repo: Optional[str],
    origin_path: Optional[str],
    filename: str,
    timestamp: datetime,
    file_hash: str,
) -> Path:
    """
    Generate deterministic snapshot path according to requirements.

    Format: <origin_repo_identifier>/<origin_path_or_filename>/snapshots/<ISO8601>-<sha256>

    Args:
        origin_repo: Origin repository URL (e.g., git@github.com:org/repo.git)
        origin_path: Path in origin repo (e.g., reports/revenue.xlsb)
        filename: Workbook filename
        timestamp: Snapshot timestamp
        file_hash: SHA256 hash of original file

    Returns:
        Relative path for snapshot in snapshot repo
    """
    # Create repo identifier from URL
    if origin_repo:
        # Extract repo name from git URL
        # git@github.com:org/repo.git -> org-repo
        # https://github.com/org/repo.git -> org-repo
        repo_part = origin_repo.split("/")[-1].replace(".git", "")
        if ":" in origin_repo:
            # SSH format: extract org/repo part
            org_repo = origin_repo.split(":")[-1].replace(".git", "")
            repo_identifier = org_repo.replace("/", "-")
        else:
            # HTTPS format
            parts = origin_repo.rstrip("/").split("/")
            if len(parts) >= 2:
                repo_identifier = f"{parts[-2]}-{parts[-1].replace('.git', '')}"
            else:
                repo_identifier = repo_part
    else:
        repo_identifier = "default"

    # Use origin_path if available, otherwise just filename
    path_part = origin_path if origin_path else filename
    # Remove file extension and sanitize
    path_part = path_part.replace("/", "-").replace("\\", "-")

    # Format timestamp as ISO8601 (filename-safe)
    timestamp_str = timestamp.strftime("%Y%m%dT%H%M%SZ")

    # Truncate hash to first 8 characters for readability
    hash_short = file_hash[:8]

    # Build path
    snapshot_path = Path(repo_identifier) / path_part / "snapshots" / f"{timestamp_str}-{hash_short}"

    return snapshot_path


def get_result_storage_path(job_id: str, result_type: str = "result") -> Path:
    """
    Get path for storing job results.

    Args:
        job_id: Job identifier
        result_type: Type of result (result, archive, etc.)

    Returns:
        Path for storing result
    """
    settings = get_settings()
    results_dir = settings.TEMP_STORAGE_PATH / "results" / job_id
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir / f"{result_type}.json"
