"""
State Manager - Centralized state management for Excel Differ

WHAT THIS FILE DOES:
    Provides a single, encapsulated class for managing all workflow state.
    All state logic is contained here - no state management scattered elsewhere.

DESIGN PRINCIPLES:
    - Single source of truth for state operations
    - Easy to extend with new attributes
    - Per-file state tracking (not global)
    - Thread-safe file operations
    - Handles state file creation, reading, writing

STATE STRUCTURE:
    {
      "version": "1.0",
      "files": {
        "path/to/file.xlsx": {
          "last_processed_version": "1730678901234",
          "last_processed_date": "2025-11-03T10:15:01.234000",
          "status": "success",  # success, failed, pending
          "last_error": null,
          "attempts": 1
        }
      },
      "metadata": {
        "last_run_date": "2025-11-03T10:15:10.000000"
      }
    }

USAGE:
    from src.utils.state_manager import StateManager, FileState

    # Initialize
    state_mgr = StateManager('./tmp/state/.excel-differ-state.json')

    # Check if file should be processed
    if state_mgr.should_process_file('data/file.xlsx', '1730678901234'):
        # Process file...

        # Update state on success
        state_mgr.update_file_state(
            file_path='data/file.xlsx',
            success=True,
            version='1730678901234',
            error=None
        )

    # Get state for specific file
    file_state = state_mgr.get_file_state('data/file.xlsx')
    if file_state.status == 'failed':
        # Retry logic...
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass, asdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class FileState:
    """
    State for a single file.

    Attributes:
        last_processed_version: Version (timestamp/hash) last successfully processed
        last_processed_date: Date of last processing attempt
        status: Current status ('success', 'failed', 'pending')
        last_error: Error message from last failure (None if success)
        attempts: Number of processing attempts
    """
    last_processed_version: Optional[str] = None
    last_processed_date: Optional[str] = None  # ISO format string
    status: str = 'pending'  # 'success', 'failed', 'pending'
    last_error: Optional[str] = None
    attempts: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'last_processed_version': self.last_processed_version,
            'last_processed_date': self.last_processed_date,
            'status': self.status,
            'last_error': self.last_error,
            'attempts': self.attempts
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FileState':
        """Create FileState from dictionary"""
        return cls(
            last_processed_version=data.get('last_processed_version'),
            last_processed_date=data.get('last_processed_date'),
            status=data.get('status', 'pending'),
            last_error=data.get('last_error'),
            attempts=data.get('attempts', 0)
        )


class StateManager:
    """
    Centralized state management for Excel Differ workflows.

    All state operations go through this class. No state logic should
    exist in source, destination, or orchestrator components.
    """

    STATE_VERSION = "1.0"

    def __init__(self, state_file_path: str):
        """
        Initialize StateManager.

        Args:
            state_file_path: Path to state file (e.g., './tmp/state/.excel-differ-state.json')
        """
        self.state_file = Path(state_file_path)
        self._lock = Lock()  # Thread-safe file access
        self._state_cache = None  # Cache to avoid repeated file reads
        logger.debug(f"Initialized StateManager with state file: {self.state_file}")

    def _load_state(self) -> dict:
        """
        Load state from file.

        Returns:
            State dictionary with structure:
            {
              "version": "1.0",
              "files": {...},
              "metadata": {...}
            }
        """
        with self._lock:
            # Return cached state if available
            if self._state_cache is not None:
                return self._state_cache

            # Create default state if file doesn't exist
            if not self.state_file.exists():
                logger.info("No state file found - creating new state")
                default_state = {
                    "version": self.STATE_VERSION,
                    "files": {},
                    "metadata": {
                        "last_run_date": None
                    }
                }
                self._state_cache = default_state
                return default_state

            # Load existing state
            try:
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)

                # Validate state version
                if state_data.get('version') != self.STATE_VERSION:
                    logger.warning(
                        f"State version mismatch: {state_data.get('version')} != {self.STATE_VERSION}. "
                        "Starting with fresh state."
                    )
                    state_data = {
                        "version": self.STATE_VERSION,
                        "files": {},
                        "metadata": {"last_run_date": None}
                    }

                self._state_cache = state_data
                logger.debug(f"Loaded state with {len(state_data.get('files', {}))} file(s)")
                return state_data

            except Exception as e:
                logger.error(f"Error loading state file: {e}. Starting with fresh state.")
                default_state = {
                    "version": self.STATE_VERSION,
                    "files": {},
                    "metadata": {"last_run_date": None}
                }
                self._state_cache = default_state
                return default_state

    def _save_state(self, state: dict) -> None:
        """
        Save state to file.

        Args:
            state: State dictionary to save
        """
        with self._lock:
            try:
                # Create parent directory if needed
                self.state_file.parent.mkdir(parents=True, exist_ok=True)

                # Write state file (atomic write with temp file)
                temp_file = self.state_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(state, f, indent=2)

                # Atomic rename
                temp_file.replace(self.state_file)

                # Update cache
                self._state_cache = state

                logger.debug(f"Saved state with {len(state.get('files', {}))} file(s)")

            except Exception as e:
                logger.error(f"Error saving state file: {e}")
                raise

    def get_file_state(self, file_path: str) -> FileState:
        """
        Get state for specific file.

        Args:
            file_path: Path to file (e.g., 'data/file.xlsx')

        Returns:
            FileState object (returns default state if file not tracked)
        """
        state = self._load_state()
        file_states = state.get('files', {})

        if file_path in file_states:
            return FileState.from_dict(file_states[file_path])
        else:
            # Return default state for new files
            return FileState()

    def update_file_state(
        self,
        file_path: str,
        success: bool,
        version: str,
        error: Optional[str] = None
    ) -> None:
        """
        Update state for a file immediately after processing.

        Args:
            file_path: Path to file (e.g., 'data/file.xlsx')
            success: Whether processing succeeded
            version: Version identifier (timestamp/commit hash)
            error: Error message if failed
        """
        state = self._load_state()

        # Get existing file state or create new one
        file_state = self.get_file_state(file_path)

        # Update file state
        file_state.attempts += 1
        file_state.last_processed_date = datetime.now().isoformat()

        if success:
            file_state.status = 'success'
            file_state.last_processed_version = version
            file_state.last_error = None
            logger.info(f"Updated state for {file_path}: SUCCESS (version: {version})")
        else:
            file_state.status = 'failed'
            file_state.last_error = error
            logger.warning(f"Updated state for {file_path}: FAILED (error: {error})")

        # Save to state
        if 'files' not in state:
            state['files'] = {}
        state['files'][file_path] = file_state.to_dict()

        # Update metadata
        state['metadata']['last_run_date'] = datetime.now().isoformat()

        # Persist to file
        self._save_state(state)

    def should_process_file(self, file_path: str, file_version: str) -> bool:
        """
        Determine if a file should be processed.

        Logic:
        - File not in state: YES (new file, will use depth parameter)
        - File status 'failed': YES (retry failed files)
        - File status 'success': YES if file_version > last_processed_version

        Args:
            file_path: Path to file
            file_version: Current version of file (timestamp/hash)

        Returns:
            True if file should be processed
        """
        file_state = self.get_file_state(file_path)

        # New file (not in state)
        if file_state.last_processed_version is None:
            logger.debug(f"File {file_path} not in state - will process")
            return True

        # Failed file (retry)
        if file_state.status == 'failed':
            logger.debug(f"File {file_path} previously failed - will retry")
            return True

        # Success file (check if new version available)
        if file_state.status == 'success':
            # Compare versions (assuming timestamp-based versions)
            try:
                file_ver_int = int(file_version)
                last_ver_int = int(file_state.last_processed_version)

                if file_ver_int > last_ver_int:
                    logger.debug(
                        f"File {file_path} has new version "
                        f"({file_version} > {file_state.last_processed_version}) - will process"
                    )
                    return True
                else:
                    logger.debug(
                        f"File {file_path} already processed at version {file_state.last_processed_version} - skip"
                    )
                    return False
            except ValueError:
                # Non-numeric version comparison (fall back to string comparison)
                if file_version != file_state.last_processed_version:
                    logger.debug(f"File {file_path} has different version - will process")
                    return True
                else:
                    logger.debug(f"File {file_path} already processed - skip")
                    return False

        # Default: process
        return True

    def get_all_file_states(self) -> Dict[str, FileState]:
        """
        Get state for all tracked files.

        Returns:
            Dictionary mapping file paths to FileState objects
        """
        state = self._load_state()
        file_states = {}

        for file_path, file_data in state.get('files', {}).items():
            file_states[file_path] = FileState.from_dict(file_data)

        return file_states

    def clear_cache(self) -> None:
        """Clear internal state cache (force reload from file on next access)"""
        with self._lock:
            self._state_cache = None
        logger.debug("Cleared state cache")
