"""
Git operations for snapshot repository management.
Handles cloning, committing, and pushing snapshot files to Repo B.
"""
import time
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import git
from git import Repo, GitCommandError

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class SnapshotRepoError(Exception):
    """Base exception for snapshot repository operations."""
    pass


class SnapshotRepoAuthError(SnapshotRepoError):
    """Exception for authentication failures."""
    pass


class SnapshotRepoManager:
    """
    Manages the snapshot repository (Repo B).
    Handles initialization, commits, and pushes.
    """

    def __init__(self):
        self.settings = get_settings()
        self.repo_url = self.settings.SNAPSHOT_REPO_URL
        self.local_path = self.settings.SNAPSHOT_REPO_LOCAL_PATH
        self.repo: Optional[Repo] = None

        # Ensure local path exists
        self.local_path.mkdir(parents=True, exist_ok=True)

    def _configure_git_user(self, repo: Repo) -> None:
        """Configure git user for commits."""
        with repo.config_writer() as config:
            config.set_value("user", "name", self.settings.GIT_USER_NAME)
            config.set_value("user", "email", self.settings.GIT_USER_EMAIL)

    def initialize(self) -> Repo:
        """
        Initialize the snapshot repository.

        - If local path is empty, clone from SNAPSHOT_REPO_URL
        - If local path exists and is a git repo, use it
        - If SNAPSHOT_REPO_URL is empty, create a new local repo

        Returns:
            Git Repo object

        Raises:
            SnapshotRepoError: If initialization fails
            SnapshotRepoAuthError: If authentication fails
        """
        if self.repo is not None:
            return self.repo

        try:
            # Check if directory is already a git repo
            if (self.local_path / ".git").exists():
                logger.info(f"Using existing git repository at {self.local_path}")
                self.repo = Repo(self.local_path)
                self._configure_git_user(self.repo)
                return self.repo

            # Check if directory is empty
            is_empty = not any(self.local_path.iterdir())

            if not is_empty and not self.repo_url:
                raise SnapshotRepoError(
                    f"Local path {self.local_path} is not empty and SNAPSHOT_REPO_URL is not configured. "
                    "Please either clear the directory or configure SNAPSHOT_REPO_URL."
                )

            if self.repo_url:
                # Clone from remote
                logger.info(f"Cloning snapshot repository from {self.repo_url}")
                try:
                    self.repo = Repo.clone_from(self.repo_url, self.local_path)
                    logger.info(f"Successfully cloned snapshot repository to {self.local_path}")
                except GitCommandError as e:
                    if "authentication" in str(e).lower() or "permission denied" in str(e).lower():
                        raise SnapshotRepoAuthError(
                            f"Git authentication failed. Please check your credentials.\n"
                            f"For SSH: Ensure SSH keys are configured (~/.ssh/id_rsa)\n"
                            f"For HTTPS: Include token in SNAPSHOT_REPO_URL\n"
                            f"Error: {e}"
                        )
                    raise SnapshotRepoError(f"Failed to clone repository: {e}")
            else:
                # Create new local repository
                logger.info(f"Creating new local git repository at {self.local_path}")
                self.repo = Repo.init(self.local_path)

                # Create initial commit
                readme_path = self.local_path / "README.md"
                readme_path.write_text("# Excel Snapshots Repository\n\nThis repository stores flattened Excel file snapshots.\n")
                self.repo.index.add([str(readme_path)])
                self.repo.index.commit("Initial commit: Initialize snapshot repository")
                logger.info("Created initial commit in snapshot repository")

            self._configure_git_user(self.repo)
            return self.repo

        except SnapshotRepoAuthError:
            raise
        except SnapshotRepoError:
            raise
        except Exception as e:
            raise SnapshotRepoError(f"Failed to initialize snapshot repository: {e}")

    def commit_snapshot(
        self,
        snapshot_dir: Path,
        original_file: Path,
        snapshot_path: Path,
        commit_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Commit a flattened snapshot to the repository.

        Args:
            snapshot_dir: Directory containing flattened snapshot
            original_file: Path to original Excel file
            snapshot_path: Relative path in repo (from get_snapshot_path)
            commit_message: Optional custom commit message
            metadata: Optional metadata dict (origin_repo, origin_commit, etc.)

        Returns:
            Commit SHA

        Raises:
            SnapshotRepoError: If commit or push fails
        """
        repo = self.initialize()

        try:
            # Determine destination paths in repo
            dest_snapshot_dir = self.local_path / snapshot_path
            dest_original_dir = dest_snapshot_dir / "original"

            # Create destination directories
            dest_snapshot_dir.mkdir(parents=True, exist_ok=True)
            dest_original_dir.mkdir(parents=True, exist_ok=True)

            # Copy snapshot files
            logger.info(f"Copying snapshot to {dest_snapshot_dir}")
            import shutil

            for item in snapshot_dir.iterdir():
                dest = dest_snapshot_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            # Copy original file
            original_dest = dest_original_dir / original_file.name
            shutil.copy2(original_file, original_dest)
            logger.info(f"Copied original file to {original_dest}")

            # Stage all files
            repo.index.add([str(snapshot_path)])

            # Generate commit message
            if not commit_message:
                if metadata and metadata.get("origin_commit_message"):
                    commit_message = metadata["origin_commit_message"]
                else:
                    from datetime import datetime, timezone
                    timestamp = datetime.now(timezone.utc).isoformat()
                    filename = original_file.name
                    commit_message = f"[excel-snapshot] Snapshot for {filename} @ {timestamp}"

            # Add metadata to commit message
            if metadata:
                commit_message += f"\n\nMetadata:"
                if metadata.get("origin_repo"):
                    commit_message += f"\n- Origin Repo: {metadata['origin_repo']}"
                if metadata.get("origin_path"):
                    commit_message += f"\n- Origin Path: {metadata['origin_path']}"
                if metadata.get("origin_commit"):
                    commit_message += f"\n- Origin Commit: {metadata['origin_commit']}"

            # Commit
            logger.info(f"Creating commit: {commit_message[:100]}...")
            commit = repo.index.commit(commit_message)
            commit_sha = commit.hexsha
            logger.info(f"Created commit: {commit_sha}")

            # Push to remote (with retry)
            if self.repo_url:
                self._push_with_retry(repo)

            return commit_sha

        except Exception as e:
            logger.exception(f"Failed to commit snapshot: {e}")
            raise SnapshotRepoError(f"Failed to commit snapshot: {e}")

    def _push_with_retry(self, repo: Repo, max_retries: int = 3, delay: int = 2) -> None:
        """
        Push to remote with retry logic for handling concurrent commits.

        Args:
            repo: Git repository object
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds

        Raises:
            SnapshotRepoError: If push fails after all retries
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Pushing to remote (attempt {attempt + 1}/{max_retries})...")

                # Pull with rebase to handle any concurrent commits
                if attempt > 0:
                    logger.info("Pulling with rebase before retry...")
                    repo.git.pull("--rebase")

                # Push
                origin = repo.remote(name="origin")
                origin.push()

                logger.info("Successfully pushed to remote")
                return

            except GitCommandError as e:
                if "authentication" in str(e).lower() or "permission denied" in str(e).lower():
                    raise SnapshotRepoAuthError(
                        f"Git authentication failed during push.\n"
                        f"For SSH: Ensure SSH keys are configured\n"
                        f"For HTTPS: Include token in SNAPSHOT_REPO_URL\n"
                        f"Error: {e}"
                    )

                if attempt < max_retries - 1:
                    logger.warning(f"Push failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    raise SnapshotRepoError(f"Failed to push after {max_retries} attempts: {e}")

    def get_snapshot(self, snapshot_path: Path) -> Optional[Path]:
        """
        Get path to a committed snapshot in the local repository.

        Args:
            snapshot_path: Relative path to snapshot in repo

        Returns:
            Absolute path to snapshot directory, or None if not found
        """
        repo = self.initialize()
        full_path = self.local_path / snapshot_path

        if full_path.exists() and full_path.is_dir():
            return full_path

        return None

    def pull_latest(self) -> None:
        """
        Pull latest changes from remote repository.

        Raises:
            SnapshotRepoError: If pull fails
        """
        if not self.repo_url:
            logger.info("No remote URL configured, skipping pull")
            return

        repo = self.initialize()

        try:
            logger.info("Pulling latest changes from remote...")
            origin = repo.remote(name="origin")
            origin.pull()
            logger.info("Successfully pulled latest changes")
        except GitCommandError as e:
            if "authentication" in str(e).lower() or "permission denied" in str(e).lower():
                raise SnapshotRepoAuthError(
                    f"Git authentication failed during pull: {e}"
                )
            raise SnapshotRepoError(f"Failed to pull from remote: {e}")


# Global instance (singleton)
_snapshot_repo_manager: Optional[SnapshotRepoManager] = None


def get_snapshot_repo_manager() -> SnapshotRepoManager:
    """
    Get the global SnapshotRepoManager instance (singleton).

    Returns:
        SnapshotRepoManager instance
    """
    global _snapshot_repo_manager

    if _snapshot_repo_manager is None:
        _snapshot_repo_manager = SnapshotRepoManager()

    return _snapshot_repo_manager
