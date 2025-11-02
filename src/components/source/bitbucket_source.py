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
        - Version = commit SHA
        - If since_version: Return files changed in commits after that SHA
        - If since_version is None: Return files changed in last N commits (depth)
        - If depth = 0: Return empty list
        """
        try:
            if self.depth == 0 and not since_version:
                logger.info("Depth is 0, returning no files")
                return []

            # Get commits using client
            if since_version:
                logger.info(f"Fetching commits since {since_version}")
                data = self.client.get_commits(branch=self.branch, exclude=since_version)
            elif self.depth > 0:
                logger.info(f"Fetching last {self.depth} commit(s)")
                data = self.client.get_commits(branch=self.branch, pagelen=self.depth)
            else:
                return []

            commits = data.get('values', [])
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

                logger.debug(f"Processing commit {commit_sha[:8]}")

                # TODO: Implement proper file listing when needed
                # For now, just return empty - user said keep it minimal

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
            logger.info(f"Downloading {source_path} at commit {version[:8]}")

            # Download using client
            content = self.client.get_file(path=source_path, ref=version)

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
        """Get current version identifier (latest commit SHA on branch)."""
        try:
            commit_sha = self.client.get_branch_head(self.branch)
            logger.debug(f"Current version: {commit_sha}")
            return commit_sha
        except Exception as e:
            logger.error(f"Error getting current version: {e}")
            # Return timestamp as fallback
            return datetime.now().isoformat()

    def get_name(self) -> str:
        """Return name of this source implementation"""
        return "BitbucketSource"
