"""
BitbucketSource - Read Excel files from Bitbucket repository

Minimal implementation - uses client for all HTTP operations.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from src.interfaces import (
    SourceInterface,
    SourceSyncState,
    SourceFileInfo,
    DownloadResult
)
from src.utils.bitbucket_client import BitbucketClient


logger = logging.getLogger(__name__)


class BitbucketSource(SourceInterface):
    """
    Bitbucket repository source implementation.

    Uses client for all HTTP operations.
    """

    def __init__(self, config: dict):
        """
        Initialize BitbucketSource.

        Args:
            config: Configuration dict with:
                - url: Full API base URL (e.g., https://api.bitbucket.org/2.0/repositories/workspace/repo)
                - branch: Branch name (required)
                - include_patterns: List of glob patterns to include (optional)
                - exclude_patterns: List of glob patterns to exclude (optional)
                - depth: Number of commits to process initially (optional, default: 1)
                - state_file_path: Path to state file (injected by factory)
        """
        super().__init__(config)
        self.url = config['url']
        self.branch = config['branch']
        self.include_patterns = config.get('include_patterns', ['**/*.xlsx', '**/*.xlsm'])
        self.exclude_patterns = config.get('exclude_patterns', [])
        self.depth = config.get('depth', 1)

        # State file path (injected by factory from workflow definition)
        self.state_file = Path(config.get('state_file_path', './.excel-differ-state.json'))

        # Initialize client - it gets token from environment automatically
        self.client = BitbucketClient(base_url=self.url)

        logger.info(f"Initialized BitbucketSource for {self.url} (branch: {self.branch})")

    def get_sync_state(self) -> SourceSyncState:
        """Get last synchronisation state from state file."""
        if not self.state_file.exists():
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

            logger.info(f"Loaded sync state: last_version={state_data.get('last_processed_version')}")

            return SourceSyncState(
                last_processed_version=state_data.get('last_processed_version'),
                last_processed_date=last_date
            )

        except Exception as e:
            logger.warning(f"Error reading state file: {e}. Treating as first run.")
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
        - Version = timestamp
        - If since_version: Return files changed in commits after that timestamp
        - If since_version is None: Return files changed in last N commits (depth)
        - If depth = 0: Return empty list
        """
        try:
            if self.depth == 0 and not since_version:
                logger.info("Depth is 0, returning no files")
                return []

            # Get commits using client
            # Fetch more commits than depth to ensure we get enough after filtering
            limit = 10 if since_version else self.depth
            data = self.client.get_commits(branch=self.branch, limit=limit)

            all_commits = data.get('values', [])
            if not all_commits:
                logger.info("No commits found")
                return []

            # Filter commits by timestamp if since_version is provided
            commits = []
            if since_version:
                logger.info(f"Filtering commits since timestamp {since_version}")
                since_timestamp = int(since_version)
                for commit in all_commits:
                    commit_timestamp = int(commit['authorTimestamp'])
                    if commit_timestamp > since_timestamp:
                        commits.append(commit)
                logger.info(f"Found {len(commits)} commits after timestamp {since_version}")
            else:
                # Just use the first N commits (depth)
                commits = all_commits[:self.depth]
                logger.info(f"Processing last {len(commits)} commit(s)")

            if not commits:
                logger.info("No new commits to process")
                return []

            # Collect changed files from all commits
            changed_files = {}  # path -> SourceFileInfo (deduplicate by path)

            for commit in commits:
                commit_id = commit['id']
                commit_timestamp = commit['authorTimestamp']
                commit_date = datetime.fromtimestamp(commit_timestamp / 1000)  # Convert ms to seconds

                logger.debug(f"Processing commit {commit['message'][:50]}")

                # Get files changed in this commit
                try:
                    changes = self.client.get_commit_changes(commit_id)

                    for change in changes.get('values', []):
                        file_path = change['path']['toString']
                        # Normalize path separators (convert Windows \ to /)
                        file_path = file_path.replace('\\', '/')
                        path_obj = Path(file_path)

                        # Check if file matches include patterns
                        included = any(path_obj.match(pattern) for pattern in self.include_patterns)
                        if not included:
                            continue

                        # Check if file matches exclude patterns
                        excluded = any(path_obj.match(pattern) for pattern in self.exclude_patterns)
                        if excluded:
                            continue

                        # Add to changed files (use latest version if file appears in multiple commits)
                        if file_path not in changed_files:
                            changed_files[file_path] = SourceFileInfo(
                                path=path_obj,
                                version=str(commit_timestamp),  # Use timestamp as version
                                version_date=commit_date,
                                status='modified'
                            )
                            logger.debug(f"Found changed file: {file_path}")

                except Exception as e:
                    logger.warning(f"Error getting changes for commit {commit_id}: {e}")
                    continue

            logger.info(f"Found {len(changed_files)} changed file(s) matching patterns")
            return list(changed_files.values())

        except Exception as e:
            logger.error(f"Error fetching commits: {e}")
            return []

    def download_file(
        self,
        source_path: str,
        version: str,
        local_dest: Path
    ) -> DownloadResult:
        """Download file from Bitbucket at specific commit."""
        try:
            logger.info(f"Downloading {source_path} at version {version}")

            # Download using client (use branch name as ref for now)
            content = self.client.get_file(path=source_path, ref=self.branch)

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

        except Exception as e:
            logger.error(f"Error downloading {source_path}: {e}")
            return DownloadResult(
                success=False,
                source_path=source_path,
                local_path=local_dest,
                version=version,
                errors=[str(e)]
            )

    def get_current_version(self) -> str:
        """Get current version identifier (latest commit timestamp on branch)."""
        try:
            commit_timestamp = self.client.get_branch_head_timestamp(self.branch)
            logger.debug(f"Current version: {commit_timestamp}")
            return commit_timestamp
        except Exception as e:
            logger.error(f"Error getting current version: {e}")
            # Return timestamp as fallback
            return datetime.now().isoformat()

    def get_name(self) -> str:
        """Return name of this source implementation"""
        return "BitbucketSource"
