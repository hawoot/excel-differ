"""
BitbucketDestination - Upload files to Bitbucket repository

Minimal implementation - uses client for all HTTP operations.
State management handled by StateManager.
"""

import logging
from pathlib import Path
from typing import List

from src.interfaces import DestinationInterface, UploadResult
from src.utils.bitbucket_client import BitbucketClient


logger = logging.getLogger(__name__)


class BitbucketDestination(DestinationInterface):
    """
    Bitbucket repository destination implementation.

    Uses client for all HTTP operations.
    """

    def __init__(self, config: dict):
        """
        Initialize BitbucketDestination.

        Args:
            config: Configuration dict with:
                - url: Full API base URL (e.g., https://api.bitbucket.org/2.0/repositories/workspace/repo)
                - branch: Branch name (required)
                - output_path: Where to upload in repo (optional, default: "")
        """
        super().__init__(config)
        self.url = config['url']
        self.branch = config['branch']
        self.output_path = config.get('output_path', '').strip('/')

        # Initialize client - it gets token from environment automatically
        self.client = BitbucketClient(base_url=self.url)

        logger.info(
            f"Initialized BitbucketDestination for {self.url} "
            f"(branch: {self.branch}, output_path: {self.output_path or 'root'})"
        )

    def upload_file(
        self,
        local_file: Path,
        remote_path: str,
        message: str
    ) -> UploadResult:
        """Upload single file to Bitbucket repository."""
        try:
            # Read file content
            with open(local_file, 'rb') as f:
                content = f.read()

            # Determine full path in repository
            repo_path = f"{self.output_path}/{remote_path}" if self.output_path else remote_path

            # Upload using client
            files = {repo_path: content}
            result = self.client.upload_files(branch=self.branch, files=files, message=message)

            # Extract commit SHA from response
            version = result.get('hash') or result.get('commit', {}).get('hash')

            logger.info(f"Uploaded {local_file.name} to {repo_path} (commit: {version})")

            return UploadResult(
                success=True,
                version=version,
                files_uploaded=[Path(repo_path)],
                message=f"Uploaded {local_file.name} to {repo_path}",
                errors=[]
            )

        except Exception as e:
            logger.error(f"Error uploading {local_file}: {e}")
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
        """Upload entire directory to Bitbucket repository in single commit."""
        try:
            # Collect all files in directory
            files_to_upload = {}
            uploaded_paths = []

            for file_path in local_dir.rglob('*'):
                if file_path.is_file():
                    # Get relative path within the directory
                    rel_path = file_path.relative_to(local_dir)

                    # Determine full path in repository
                    repo_path = f"{self.output_path}/{remote_path}/{rel_path}" if self.output_path else f"{remote_path}/{rel_path}"
                    repo_path = repo_path.replace('\\', '/')  # Normalize path separators

                    # Read file content
                    with open(file_path, 'rb') as f:
                        files_to_upload[repo_path] = (repo_path, f.read())

                    uploaded_paths.append(Path(repo_path))

            if not files_to_upload:
                logger.warning(f"No files found in {local_dir}")
                return UploadResult(
                    success=True,
                    version=None,
                    files_uploaded=[],
                    message=f"No files to upload from {local_dir}",
                    errors=[]
                )

            # Upload all files in a single commit using client
            result = self.client.upload_files(branch=self.branch, files=files_to_upload, message=message)

            # Extract commit SHA from response
            version = result.get('hash') or result.get('commit', {}).get('hash')

            logger.info(
                f"Uploaded directory {local_dir.name} to {remote_path} "
                f"({len(files_to_upload)} files, commit: {version})"
            )

            return UploadResult(
                success=True,
                version=version,
                files_uploaded=uploaded_paths,
                message=f"Uploaded directory {local_dir.name} to {remote_path} ({len(files_to_upload)} files)",
                errors=[]
            )

        except Exception as e:
            logger.error(f"Error uploading directory {local_dir}: {e}")
            return UploadResult(
                success=False,
                version=None,
                files_uploaded=[],
                message=f"Directory upload failed: {str(e)}",
                errors=[str(e)]
            )

    def get_name(self) -> str:
        """Return name of this destination implementation"""
        return "BitbucketDestination"
