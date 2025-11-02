"""
BitbucketDestination - Upload files to Bitbucket repository

Uploads flattened Excel files to a Bitbucket repository using Bitbucket Cloud API v2.0.
Maintains sync state in the repository.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from src.interfaces import DestinationInterface, SourceSyncState, UploadResult
from src.components.common.bitbucket_client import BitbucketClient, BitbucketError


logger = logging.getLogger(__name__)


class BitbucketDestination(DestinationInterface):
    """
    Bitbucket repository destination implementation.

    Uploads files to a Bitbucket repository and tracks sync state in the repo.
    """

    def __init__(self, config: dict):
        """
        Initialize BitbucketDestination.

        Args:
            config: Configuration dict with:
                - url: Repository URL (e.g., https://bitbucket.org/workspace/repo)
                - branch: Branch name (required)
                - token: App password or access token (required)
                - output_path: Where to upload in repo (optional, default: "")
                - state_file_path: Path to state file (injected by factory)
        """
        super().__init__(config)
        self.url = config['url']
        self.branch = config['branch']
        self.token = config['token']
        self.output_path = config.get('output_path', '').strip('/')

        # Parse repository URL to extract workspace and repo_slug
        self.workspace, self.repo_slug = self._parse_url(self.url)

        # State file path (injected by factory from workflow definition)
        # Note: For Bitbucket destination, this is the local path where we'll
        # temporarily write the state before uploading to the repo
        self.state_file = Path(config.get('state_file_path', './.excel-differ-state.json'))
        self.state_file_name = self.state_file.name  # Filename to use in repo

        # Initialize Bitbucket client
        self.client = BitbucketClient(
            workspace=self.workspace,
            repo_slug=self.repo_slug,
            token=self.token
        )

        logger.info(
            f"Initialized BitbucketDestination for {self.workspace}/{self.repo_slug} "
            f"(branch: {self.branch}, output_path: {self.output_path or 'root'})"
        )

    def _parse_url(self, url: str) -> tuple[str, str]:
        """
        Parse Bitbucket repository URL to extract workspace and repo slug.

        Args:
            url: Repository URL (e.g., https://bitbucket.org/workspace/repo)

        Returns:
            Tuple of (workspace, repo_slug)

        Raises:
            ValueError: If URL cannot be parsed
        """
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')

        if len(path_parts) < 2:
            raise ValueError(
                f"Invalid Bitbucket URL: {url}. "
                "Expected format: https://bitbucket.org/workspace/repo"
            )

        workspace = path_parts[0]
        repo_slug = path_parts[1]

        return workspace, repo_slug

    def save_sync_state(self, state: SourceSyncState) -> None:
        """
        Save synchronisation state.

        Uploads state file to the Bitbucket repository.

        Args:
            state: SourceSyncState to save
        """
        state_data = {
            'last_processed_version': state.last_processed_version,
            'last_processed_date': state.last_processed_date.isoformat() if state.last_processed_date else None
        }

        try:
            # Write state to local file first
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)

            # Upload state file to repository
            with open(self.state_file, 'rb') as f:
                state_content = f.read()

            # Determine path in repository
            repo_path = f"{self.output_path}/{self.state_file_name}" if self.output_path else self.state_file_name

            self.client.upload_files(
                branch=self.branch,
                files={repo_path: state_content},
                message=f"Update sync state: {state.last_processed_version}"
            )

            logger.info(f"Saved sync state to {repo_path}")

        except Exception as e:
            logger.error(f"Error saving sync state: {e}")
            raise

    def upload_file(
        self,
        local_file: Path,
        remote_path: str,
        message: str
    ) -> UploadResult:
        """
        Upload single file to Bitbucket repository.

        Args:
            local_file: Path to local file to upload
            remote_path: Relative path in repository (e.g., "flat/workbook.xlsx")
            message: Commit message

        Returns:
            UploadResult with success status
        """
        try:
            # Read file content
            with open(local_file, 'rb') as f:
                content = f.read()

            # Determine full path in repository
            repo_path = f"{self.output_path}/{remote_path}" if self.output_path else remote_path

            # Upload to Bitbucket
            response = self.client.upload_files(
                branch=self.branch,
                files={repo_path: content},
                message=message
            )

            # Extract commit SHA from response
            # The response structure varies, but typically includes a commit hash
            version = None
            if isinstance(response, dict):
                # Try to extract hash from various possible locations
                version = (
                    response.get('hash') or
                    response.get('commit', {}).get('hash') or
                    response.get('parents', [{}])[0].get('hash')
                )

            logger.info(f"Uploaded {local_file.name} to {repo_path} (commit: {version})")

            return UploadResult(
                success=True,
                version=version,
                files_uploaded=[Path(repo_path)],
                message=f"Uploaded {local_file.name} to {repo_path}",
                errors=[]
            )

        except BitbucketError as e:
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
        """
        Upload entire directory to Bitbucket repository.

        Creates a single commit with all files in the directory.

        Args:
            local_dir: Path to local directory to upload
            remote_path: Relative path in repository (e.g., "flattened/workbook-flat/")
            message: Commit message

        Returns:
            UploadResult with success status and list of uploaded files
        """
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
                        files_to_upload[repo_path] = f.read()

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

            # Upload all files in a single commit
            response = self.client.upload_files(
                branch=self.branch,
                files=files_to_upload,
                message=message
            )

            # Extract commit SHA from response
            version = None
            if isinstance(response, dict):
                version = (
                    response.get('hash') or
                    response.get('commit', {}).get('hash') or
                    response.get('parents', [{}])[0].get('hash')
                )

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

        except BitbucketError as e:
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
