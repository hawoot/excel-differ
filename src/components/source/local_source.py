"""
LocalSource - Read Excel files from local folder

Simple source that scans a local directory for Excel files.
Tracks changes using file modification timestamps.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from fnmatch import fnmatch

from src.interfaces import (
    SourceInterface,
    SourceSyncState,
    SourceFileInfo,
    DownloadResult
)


class LocalSource(SourceInterface):
    """
    Local folder source implementation.

    Scans a local directory for Excel files matching patterns.
    Uses file modification times for versioning.
    """

    def __init__(self, config: dict):
        """
        Initialize LocalSource.

        Args:
            config: Configuration dict with:
                - folder_path: Source folder path (required)
                - include_patterns: List of glob patterns to include (optional)
                - exclude_patterns: List of glob patterns to exclude (optional)
                - destination_folder: Where to read sync state from (required)
        """
        super().__init__(config)
        self.folder_path = Path(config['folder_path'])
        self.include_patterns = config.get('include_patterns', ['*.xlsx', '*.xlsm', '**/*.xlsx', '**/*.xlsm'])
        self.exclude_patterns = config.get('exclude_patterns', [])

        # Destination folder for reading sync state
        self.destination_folder = Path(config.get('destination_folder', './output'))
        self.state_file = self.destination_folder / '.excel-differ-state.json'

        if not self.folder_path.exists():
            raise ValueError(f"Source folder does not exist: {self.folder_path}")

    def get_sync_state(self) -> SourceSyncState:
        """
        Get last synchronisation state from destination.

        Reads .excel-differ-state.json from destination folder.

        Returns:
            SourceSyncState with last processed version and date,
            or None values if first run
        """
        if not self.state_file.exists():
            # First run - no state file
            return SourceSyncState(
                last_processed_version=None,
                last_processed_date=None
            )

        try:
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)

            last_date = None
            if state_data.get('last_processed_date'):
                last_date = datetime.fromisoformat(state_data['last_processed_date'])

            return SourceSyncState(
                last_processed_version=state_data.get('last_processed_version'),
                last_processed_date=last_date
            )

        except Exception as e:
            # Error reading state - treat as first run
            return SourceSyncState(
                last_processed_version=None,
                last_processed_date=None
            )

    def get_changed_files(
        self,
        since_version: Optional[str],
    ) -> List[SourceFileInfo]:
        """
        Get files that have changed.

        For local source:
        - Version = ISO timestamp string
        - If since_version: Return files modified after that timestamp
        - If depth > 0: Return all matching files (depth ignored for local)
        - If depth = 0: Return empty list

        Args:
            include_patterns: Glob patterns to include
            exclude_patterns: Glob patterns to exclude
            since_version: ISO timestamp to get changes since
            depth: Ignored for local source (0 = return nothing, >0 = return all)

        Returns:
            List of SourceFileInfo for matching files
        """

        # Scan folder for files matching patterns
        matching_files = []

        for file_path in self.folder_path.rglob('*'):
            if not file_path.is_file():
                continue

            # Get relative path for pattern matching
            rel_path = file_path.relative_to(self.folder_path)
            rel_path_str = str(rel_path)

            # Check include patterns (use Path.match for ** support)
            included = any(
                rel_path.match(pattern)
                for pattern in self.include_patterns
            )

            if not included:
                continue

            # Check exclude patterns (use Path.match for ** support)
            excluded = any(
                rel_path.match(pattern)
                for pattern in self.exclude_patterns
            )

            if excluded:
                continue

            # Get file modification time
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            version = mtime.isoformat()

            # If since_version specified, check if file is newer
            if since_version:
                try:
                    since_date = datetime.fromisoformat(since_version)
                    if mtime <= since_date:
                        continue  # File hasn't changed
                except:
                    pass  # Invalid since_version, include file anyway

            # Determine status (for local, always 'modified' since we can't track adds/deletes)
            matching_files.append(
                SourceFileInfo(
                    path=rel_path,
                    version=version,
                    version_date=mtime,
                    status='modified'
                )
            )

        return matching_files

    def download_file(
        self,
        source_path: str,
        version: str,
        local_dest: Path
    ) -> DownloadResult:
        """
        Download file (actually just copy it locally).

        For local source, this just copies the file since it's already local.

        Args:
            source_path: Relative path in source folder
            version: Version (timestamp) - not used for local
            local_dest: Where to copy the file

        Returns:
            DownloadResult with success status
        """
        try:
            source_file = self.folder_path / source_path

            if not source_file.exists():
                return DownloadResult(
                    success=False,
                    source_path=source_path,
                    local_path=local_dest,
                    version=version,
                    errors=[f"Source file not found: {source_file}"]
                )

            # Create parent directory if needed
            local_dest.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source_file, local_dest)

            return DownloadResult(
                success=True,
                source_path=source_path,
                local_path=local_dest,
                version=version,
                errors=[]
            )

        except Exception as e:
            return DownloadResult(
                success=False,
                source_path=source_path,
                local_path=local_dest,
                version=version,
                errors=[str(e)]
            )

    def get_current_version(self) -> str:
        """
        Get current version identifier.

        For local source, this is the current timestamp.

        Returns:
            ISO timestamp string
        """
        return datetime.now().isoformat()

    def get_name(self) -> str:
        """Return name of this source implementation"""
        return "LocalSource"
