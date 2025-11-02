"""
BitbucketSource - Read Excel files from Bitbucket repository

Fetches files from a Bitbucket repository using Bitbucket Cloud API v2.0.
Tracks changes using commit SHAs.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from src.interfaces import (
    SourceInterface,
    SourceSyncState,
    SourceFileInfo,
    DownloadResult
)
from src.components.common.bitbucket_client import BitbucketClient, BitbucketError


logger = logging.getLogger(__name__)


class BitbucketSource(SourceInterface):
    """
    Bitbucket repository source implementation.

    Fetches Excel files from a Bitbucket repository matching patterns.
    Uses commit SHAs for versioning.
    """

    def __init__(self, config: dict):
        """
        Initialize BitbucketSource.

        Args:
            config: Configuration dict with:
                - url: Repository URL (e.g., https://bitbucket.org/workspace/repo)
                - branch: Branch name (required)
                - token: App password or access token (required)
                - include_patterns: List of glob patterns to include (optional)
                - exclude_patterns: List of glob patterns to exclude (optional)
                - depth: Number of commits to process initially (optional, default: 1)
                - state_file_path: Path to state file (injected by factory)
        """
        super().__init__(config)
        self.url = config['url']
        self.branch = config['branch']
        self.token = config['token']
        self.include_patterns = config.get('include_patterns', ['**/*.xlsx', '**/*.xlsm'])
        self.exclude_patterns = config.get('exclude_patterns', [])
        self.depth = config.get('depth', 1)

        # Parse repository URL to extract workspace and repo_slug
        self.workspace, self.repo_slug = self._parse_url(self.url)

        # State file path (injected by factory from workflow definition)
        self.state_file = Path(config.get('state_file_path', './.excel-differ-state.json'))

        # Initialize Bitbucket client
        self.client = BitbucketClient(
            workspace=self.workspace,
            repo_slug=self.repo_slug,
            token=self.token
        )

        logger.info(
            f"Initialized BitbucketSource for {self.workspace}/{self.repo_slug} "
            f"(branch: {self.branch})"
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

    def get_sync_state(self) -> SourceSyncState:
        """
        Get last synchronisation state.

        Reads state file from configured path.

        Returns:
            SourceSyncState with last processed version (commit SHA) and date,
            or None values if first run
        """
        if not self.state_file.exists():
            # First run - no state file
            logger.info("No sync state file found - first run")
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

            logger.info(
                f"Loaded sync state: last_version={state_data.get('last_processed_version')}"
            )

            return SourceSyncState(
                last_processed_version=state_data.get('last_processed_version'),
                last_processed_date=last_date
            )

        except Exception as e:
            logger.warning(f"Error reading state file: {e}. Treating as first run.")
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

        For Bitbucket source:
        - Version = commit SHA
        - If since_version: Return files changed in commits after that SHA
        - If since_version is None: Return files changed in last N commits (depth)
        - If depth = 0: Return empty list

        Args:
            since_version: Commit SHA to get changes since

        Returns:
            List of SourceFileInfo for matching files
        """
        try:
            # Get commits to process
            if since_version:
                # Get commits since the last processed version
                logger.info(f"Fetching commits since {since_version}")
                commits = self.client.list_commits(
                    branch=self.branch,
                    since=since_version
                )
            elif self.depth > 0:
                # First run or no previous state - get last N commits
                logger.info(f"Fetching last {self.depth} commit(s)")
                commits = self.client.list_commits(
                    branch=self.branch,
                    limit=self.depth
                )
            else:
                # Depth = 0, return nothing
                logger.info("Depth is 0, returning no files")
                return []

            if not commits:
                logger.info("No commits found to process")
                return []

            logger.info(f"Processing {len(commits)} commit(s)")

            # Collect changed files from all commits
            changed_files = {}  # path -> SourceFileInfo (deduplicate by path)

            for commit in commits:
                commit_sha = commit['hash']
                commit_date_str = commit['date']
                commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))

                logger.debug(f"Processing commit {commit_sha[:8]}: {commit.get('message', '')[:50]}")

                # Get files changed in this commit
                try:
                    # List all files in the repository at this commit
                    # and filter by patterns
                    files_in_commit = self._get_matching_files_at_commit(commit_sha)

                    for file_path in files_in_commit:
                        # Use the latest version of each file (commits are in reverse chronological order)
                        if file_path not in changed_files:
                            changed_files[file_path] = SourceFileInfo(
                                path=Path(file_path),
                                version=commit_sha,
                                version_date=commit_date,
                                status='modified'  # We don't distinguish add/modify/delete yet
                            )

                except BitbucketError as e:
                    logger.warning(f"Error processing commit {commit_sha}: {e}")
                    continue

            result = list(changed_files.values())
            logger.info(f"Found {len(result)} changed file(s) matching patterns")
            return result

        except BitbucketError as e:
            logger.error(f"Error fetching commits: {e}")
            return []

    def _get_matching_files_at_commit(self, commit_sha: str) -> List[str]:
        """
        Get list of files at a specific commit that match include/exclude patterns.

        Args:
            commit_sha: Commit SHA

        Returns:
            List of file paths matching patterns
        """
        matching_files = []

        try:
            # List files in repository root at this commit
            # Note: We need to recursively traverse directories
            matching_files = self._list_files_recursive('', commit_sha)

        except BitbucketError as e:
            logger.warning(f"Error listing files at commit {commit_sha}: {e}")

        return matching_files

    def _list_files_recursive(self, path: str, commit_sha: str) -> List[str]:
        """
        Recursively list all files in a directory at a specific commit.

        Args:
            path: Directory path (empty string for root)
            commit_sha: Commit SHA

        Returns:
            List of file paths matching patterns
        """
        matching_files = []

        try:
            items = self.client.list_directory(path=path, ref=commit_sha)

            for item in items:
                item_path = item['path']
                item_type = item.get('type', 'commit_file')

                if item_type == 'commit_directory':
                    # Recursively list subdirectory
                    matching_files.extend(
                        self._list_files_recursive(item_path, commit_sha)
                    )
                elif item_type == 'commit_file':
                    # Check if file matches patterns
                    if self._matches_patterns(item_path):
                        matching_files.append(item_path)

        except BitbucketError as e:
            logger.debug(f"Error listing directory {path}: {e}")

        return matching_files

    def _matches_patterns(self, file_path: str) -> bool:
        """
        Check if a file path matches include/exclude patterns.

        Args:
            file_path: File path to check

        Returns:
            True if file matches patterns, False otherwise
        """
        path_obj = Path(file_path)

        # Check include patterns
        included = any(
            path_obj.match(pattern)
            for pattern in self.include_patterns
        )

        if not included:
            return False

        # Check exclude patterns
        excluded = any(
            path_obj.match(pattern)
            for pattern in self.exclude_patterns
        )

        return not excluded

    def download_file(
        self,
        source_path: str,
        version: str,
        local_dest: Path
    ) -> DownloadResult:
        """
        Download file from Bitbucket at specific commit.

        Args:
            source_path: Relative path in repository
            version: Commit SHA
            local_dest: Where to save the file locally

        Returns:
            DownloadResult with success status
        """
        try:
            logger.info(f"Downloading {source_path} at commit {version[:8]}")

            # Download file content
            content = self.client.get_file(source_path, ref=version)

            # Create parent directory if needed
            local_dest.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(local_dest, 'wb') as f:
                f.write(content)

            logger.info(f"Successfully downloaded {source_path} ({len(content)} bytes)")

            return DownloadResult(
                success=True,
                source_path=source_path,
                local_path=local_dest,
                version=version,
                errors=[]
            )

        except BitbucketError as e:
            logger.error(f"Error downloading {source_path}: {e}")
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

        For Bitbucket source, this is the latest commit SHA on the branch.

        Returns:
            Commit SHA of branch head
        """
        try:
            commit_sha = self.client.get_branch_head(self.branch)
            logger.debug(f"Current version: {commit_sha}")
            return commit_sha
        except BitbucketError as e:
            logger.error(f"Error getting current version: {e}")
            # Return a timestamp as fallback
            return datetime.now().isoformat()

    def get_name(self) -> str:
        """Return name of this source implementation"""
        return "BitbucketSource"
