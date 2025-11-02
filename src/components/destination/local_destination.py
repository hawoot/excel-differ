"""
LocalDestination - Save files to local folder

Simple destination that writes files to a local directory.
Maintains sync state in configured state file.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List

from src.interfaces import DestinationInterface, SourceSyncState, UploadResult


class LocalDestination(DestinationInterface):
    """
    Local folder destination implementation.

    Saves files to a local directory and tracks sync state.
    """

    def __init__(self, config: dict):
        """
        Initialize LocalDestination.

        Args:
            config: Configuration dict with:
                - folder_path: Destination folder path (required)
                - state_file_path: Path to state file (injected by factory)
        """
        super().__init__(config)
        self.folder_path = Path(config['folder_path'])
        self.state_file = Path(config.get('state_file_path', './.excel-differ-state.json'))

        # Create destination folder if it doesn't exist
        self.folder_path.mkdir(parents=True, exist_ok=True)

        # Create state file parent directory if it doesn't exist
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def save_sync_state(self, state: SourceSyncState) -> None:
        """
        Save synchronisation state.

        Writes state file with last processed version and date.

        Args:
            state: SourceSyncState to save
        """
        state_data = {
            'last_processed_version': state.last_processed_version,
            'last_processed_date': state.last_processed_date.isoformat() if state.last_processed_date else None
        }

        with open(self.state_file, 'w') as f:
            json.dump(state_data, f, indent=2)

    def upload_file(
        self,
        local_file: Path,
        remote_path: str,
        message: str
    ) -> UploadResult:
        """
        Upload single file to destination folder.

        Args:
            local_file: Path to local file to upload
            remote_path: Relative path in destination (e.g., "flat/workbook.xlsx")
            message: Upload message (not used for local, kept for interface compliance)

        Returns:
            UploadResult with success status
        """
        try:
            # Determine destination path
            dest_path = self.folder_path / remote_path

            # Create parent directories if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(local_file, dest_path)

            # Get version (current timestamp)
            version = datetime.now().isoformat()

            return UploadResult(
                success=True,
                version=version,
                files_uploaded=[dest_path],
                message=f"Uploaded {local_file.name} to {dest_path}",
                errors=[]
            )

        except Exception as e:
            return UploadResult(
                success=False,
                version=None,
                files_uploaded=[],
                message=f"Upload failed: {str(e)}",
                errors=[str(e)]
            )

    def upload_directory(
        self,
        local_dir: Path,
        remote_path: str,
        message: str
    ) -> UploadResult:
        """
        Upload entire directory to destination folder.

        Args:
            local_dir: Path to local directory to upload
            remote_path: Relative path in destination (e.g., "flattened/workbook-flat/")
            message: Upload message (not used for local, kept for interface compliance)

        Returns:
            UploadResult with success status and list of uploaded files
        """
        try:
            # Determine destination path
            dest_path = self.folder_path / remote_path

            # Remove destination if it exists (full replacement)
            if dest_path.exists():
                shutil.rmtree(dest_path)

            # Copy entire directory tree
            shutil.copytree(local_dir, dest_path)

            # List all uploaded files
            uploaded_files: List[Path] = list(dest_path.rglob('*'))
            uploaded_files = [f for f in uploaded_files if f.is_file()]

            # Get version (current timestamp)
            version = datetime.now().isoformat()

            return UploadResult(
                success=True,
                version=version,
                files_uploaded=uploaded_files,
                message=f"Uploaded directory {local_dir.name} to {dest_path} ({len(uploaded_files)} files)",
                errors=[]
            )

        except Exception as e:
            return UploadResult(
                success=False,
                version=None,
                files_uploaded=[],
                message=f"Directory upload failed: {str(e)}",
                errors=[str(e)]
            )

    def get_name(self) -> str:
        """Return name of this destination implementation"""
        return "LocalDestination"
