"""
Manifest generation for flattened snapshots.
Creates manifest.json with all required metadata.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging

from src.core.storage import get_file_hash

logger = logging.getLogger(__name__)


class Manifest:
    """
    Manifest for a flattened Excel snapshot.
    Contains metadata about the extraction process and file inventory.
    """

    def __init__(
        self,
        workbook_filename: str,
        original_sha256: str,
        extractor_version: str = "0.1.0",
        include_evaluated: bool = False,
    ):
        self.workbook_filename = workbook_filename
        self.original_sha256 = original_sha256
        self.extracted_at = datetime.now(timezone.utc).isoformat()
        self.extractor_version = extractor_version
        self.include_evaluated = include_evaluated
        self.sheets: List[Dict[str, Any]] = []
        self.files: List[Dict[str, str]] = []
        self.warnings: List[str] = []
        self.origin: Dict[str, Any] = {}

    def add_sheet(
        self,
        index: int,
        name: str,
        sheetId: int,
        visible: bool = True,
        **kwargs
    ) -> None:
        """
        Add a sheet to the manifest.

        Args:
            index: Sheet index (1-based)
            name: Sheet name
            sheetId: Excel sheet ID
            visible: Whether sheet is visible
            **kwargs: Additional sheet metadata
        """
        sheet_info = {
            "index": index,
            "name": name,
            "sheetId": sheetId,
            "visible": visible,
        }
        sheet_info.update(kwargs)
        self.sheets.append(sheet_info)

    def add_file(self, file_path: Path, snapshot_root: Path) -> None:
        """
        Add a file to the manifest with its hash.

        Args:
            file_path: Absolute path to file
            snapshot_root: Root directory of snapshot (for relative path)
        """
        if not file_path.exists():
            logger.warning(f"File not found, skipping from manifest: {file_path}")
            return

        try:
            relative_path = file_path.relative_to(snapshot_root)
            file_hash = get_file_hash(file_path)

            self.files.append({
                "path": str(relative_path).replace("\\", "/"),  # Use forward slashes
                "sha256": file_hash,
            })
        except Exception as e:
            logger.warning(f"Failed to add file to manifest: {file_path}: {e}")

    def add_warning(self, warning: str) -> None:
        """
        Add a warning message to the manifest.

        Args:
            warning: Warning message
        """
        if warning not in self.warnings:
            self.warnings.append(warning)
            logger.warning(f"Manifest warning: {warning}")

    def set_origin(
        self,
        origin_repo: Optional[str] = None,
        origin_path: Optional[str] = None,
        origin_commit: Optional[str] = None,
        origin_commit_message: Optional[str] = None,
    ) -> None:
        """
        Set origin repository information.

        Args:
            origin_repo: Origin repository URL
            origin_path: Path in origin repository
            origin_commit: Origin commit SHA
            origin_commit_message: Origin commit message
        """
        if origin_repo:
            self.origin["origin_repo"] = origin_repo
        if origin_path:
            self.origin["origin_path"] = origin_path
        if origin_commit:
            self.origin["origin_commit"] = origin_commit
        if origin_commit_message:
            self.origin["origin_commit_message"] = origin_commit_message

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert manifest to dictionary.

        Returns:
            Dictionary representation of manifest
        """
        data = {
            "workbook_filename": self.workbook_filename,
            "original_sha256": self.original_sha256,
            "extracted_at": self.extracted_at,
            "extractor_version": self.extractor_version,
            "include_evaluated": self.include_evaluated,
            "sheets": self.sheets,
            "files": sorted(self.files, key=lambda x: x["path"]),  # Sort for determinism
            "warnings": self.warnings,
        }

        if self.origin:
            data["origin"] = self.origin

        return data

    def save(self, output_path: Path) -> None:
        """
        Save manifest to JSON file.

        Args:
            output_path: Path to output file (manifest.json)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved manifest to: {output_path}")

    @classmethod
    def load(cls, manifest_path: Path) -> "Manifest":
        """
        Load manifest from JSON file.

        Args:
            manifest_path: Path to manifest.json

        Returns:
            Manifest object
        """
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        manifest = cls(
            workbook_filename=data["workbook_filename"],
            original_sha256=data["original_sha256"],
            extractor_version=data.get("extractor_version", "unknown"),
            include_evaluated=data.get("include_evaluated", False),
        )

        manifest.extracted_at = data.get("extracted_at", "")
        manifest.sheets = data.get("sheets", [])
        manifest.files = data.get("files", [])
        manifest.warnings = data.get("warnings", [])
        manifest.origin = data.get("origin", {})

        return manifest


def create_snapshot_root_name(filename: str, timestamp: datetime, file_hash: str) -> str:
    """
    Create deterministic snapshot root directory name.

    Format: <workbook_filename>-snapshot-<ISO8601>-<sha256_short>

    Args:
        filename: Workbook filename (without path)
        timestamp: Snapshot timestamp
        file_hash: SHA256 hash of original file

    Returns:
        Snapshot root directory name
    """
    # Remove extension from filename
    base_name = Path(filename).stem

    # Format timestamp (filename-safe)
    timestamp_str = timestamp.strftime("%Y%m%dT%H%M%SZ")

    # Truncate hash to first 8 characters
    hash_short = file_hash[:8]

    return f"{base_name}-snapshot-{timestamp_str}-{hash_short}"
