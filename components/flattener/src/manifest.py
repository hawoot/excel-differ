"""
Manifest generation for flattened Excel workbooks.

The manifest is a JSON file that describes the extraction and lists all files.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import get_file_hash

logger = logging.getLogger(__name__)


class Manifest:
    """
    Manifest for a flattened Excel workbook.

    Tracks extraction metadata, file inventory, warnings, and origin information.
    """

    VERSION = "2.1.0"

    def __init__(
        self,
        workbook_filename: str,
        original_sha256: str,
        include_computed: bool = False,
    ):
        """
        Initialise a new manifest.

        Args:
            workbook_filename: Name of original Excel file
            original_sha256: SHA256 hash of original file
            include_computed: Whether computed values were extracted
        """
        self.workbook_filename = workbook_filename
        self.original_sha256 = original_sha256
        self.extracted_at = datetime.now(timezone.utc).isoformat()
        self.extractor_version = self.VERSION
        self.include_computed = include_computed

        self.sheets: List[Dict[str, Any]] = []
        self.files: List[Dict[str, str]] = []
        self.warnings: List[str] = []
        self.origin: Optional[Dict[str, Any]] = None

        logger.debug(f"Manifest initialised for {workbook_filename}")

    def add_sheet(
        self,
        index: int,
        name: str,
        sheetId: int,
        visible: bool
    ) -> None:
        """
        Add a sheet to the manifest.

        Args:
            index: 1-based sheet position
            name: Sheet name
            sheetId: Excel internal sheet ID
            visible: Whether sheet is visible
        """
        sheet_info = {
            'index': index,
            'name': name,
            'sheetId': sheetId,
            'visible': visible
        }
        self.sheets.append(sheet_info)
        logger.debug(f"Added sheet to manifest: {name} (index={index})")

    def add_file(self, file_path: Path, flat_root: Path) -> None:
        """
        Add a file to the manifest with its hash.

        Args:
            file_path: Absolute path to file
            flat_root: Path to flat root directory
        """
        # Calculate relative path from flat root
        try:
            relative_path = file_path.relative_to(flat_root)
        except ValueError:
            logger.warning(f"File {file_path} is not under flat root {flat_root}")
            return

        # Calculate file hash
        file_hash = get_file_hash(file_path)

        file_info = {
            'path': str(relative_path).replace('\\', '/'),  # Use forward slashes
            'sha256': file_hash
        }
        self.files.append(file_info)
        logger.debug(f"Added file to manifest: {relative_path}")

    def add_warning(self, message: str) -> None:
        """
        Add a warning message to the manifest.

        Args:
            message: Warning message
        """
        self.warnings.append(message)
        logger.warning(f"Manifest warning: {message}")

    def set_origin(
        self,
        origin_repo: Optional[str] = None,
        origin_path: Optional[str] = None,
        origin_commit: Optional[str] = None,
        origin_commit_message: Optional[str] = None,
    ) -> None:
        """
        Set origin information for the workbook.

        Args:
            origin_repo: Git repository URL
            origin_path: Path to file in repository
            origin_commit: Git commit SHA
            origin_commit_message: Commit message
        """
        if any([origin_repo, origin_path, origin_commit, origin_commit_message]):
            self.origin = {
                'origin_repo': origin_repo or '',
                'origin_path': origin_path or '',
                'origin_commit': origin_commit or '',
                'origin_commit_message': origin_commit_message or ''
            }
            logger.debug(f"Set origin: {origin_repo}/{origin_path}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert manifest to dictionary.

        Returns:
            Dictionary representation of manifest
        """
        data = {
            'workbook_filename': self.workbook_filename,
            'original_sha256': self.original_sha256,
            'extracted_at': self.extracted_at,
            'extractor_version': self.extractor_version,
            'include_computed': self.include_computed,
            'sheets': self.sheets,
            'files': self.files,
            'warnings': self.warnings,
        }

        if self.origin:
            data['origin'] = self.origin

        return data

    def save(self, path: Path) -> None:
        """
        Save manifest to JSON file.

        Args:
            path: Path to manifest file (typically manifest.json)
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved manifest: {path}")

    @classmethod
    def load(cls, path: Path) -> 'Manifest':
        """
        Load manifest from JSON file.

        Args:
            path: Path to manifest file

        Returns:
            Manifest instance
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        manifest = cls(
            workbook_filename=data['workbook_filename'],
            original_sha256=data['original_sha256'],
            include_computed=data.get('include_computed', False)
        )

        manifest.extracted_at = data.get('extracted_at', '')
        manifest.extractor_version = data.get('extractor_version', '')
        manifest.sheets = data.get('sheets', [])
        manifest.files = data.get('files', [])
        manifest.warnings = data.get('warnings', [])
        manifest.origin = data.get('origin')

        logger.info(f"Loaded manifest: {path}")

        return manifest
