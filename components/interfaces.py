"""
Excel Differ - Component Interfaces

WHAT THIS FILE DOES:
    Defines the abstract interfaces (contracts) that all Excel Differ components
    must implement. These are the "rules" for building plugins.

RELATIONSHIP TO OTHER FILES:
    - workflows/workflow_schema.py uses these interface names in WorkflowDefinition
    - component_registry.py stores implementations of these interfaces
    - Component implementations (source/*, destination/*, etc.) inherit from these
    - workflows/workflow_loader.py doesn't directly use this (it creates config objects)

THE FOUR CORE INTERFACES:
    1. SourceInterface - Get Excel files from somewhere (Bitbucket, local folder)
    2. DestinationInterface - Upload flattened results somewhere
    3. ConverterInterface - Convert Excel files if needed (.xlsb → .xlsm)
    4. FlattenerInterface - Flatten Excel files to text

EXAMPLE USAGE:
    # Implementing a new source
    from components.interfaces import SourceInterface, SourceSyncState, SourceFileInfo

    class MyCustomSource(SourceInterface):
        def __init__(self, config: dict):
            self.config = config

        def get_sync_state(self) -> SourceSyncState:
            # Read .excel-differ-state.json from destination
            return SourceSyncState(
                last_processed_version='abc123',
                last_processed_date=datetime.now()
            )

        def get_changed_files(
            self,
            include_patterns: List[str],
            exclude_patterns: List[str],
            since_version: Optional[str],
            depth: int
        ) -> List[SourceFileInfo]:
            # Find changed files matching patterns
            return [SourceFileInfo(...)]

        def download_file(self, source_path: str, version: str, local_dest: Path) -> DownloadResult:
            # Download file to local destination
            return DownloadResult(success=True, ...)

        def get_current_version(self) -> str:
            # Return current version identifier
            return 'v2025-11-01'

        def get_name(self) -> str:
            return 'MyCustomSource'

    # Register it
    from components.component_registry import registry
    registry.register_source('my_custom', MyCustomSource)

    # Later: Use it in workflow YAML
    # source:
    #   implementation: my_custom
    #   config:
    #     custom_setting: value

DATA CLASSES:
    This file also defines data classes used by the interfaces:
    - SourceFileInfo, SourceSyncState, DownloadResult (used by SourceInterface)
    - UploadResult (used by DestinationInterface)
    - ConversionResult (used by ConverterInterface)
    - FlattenResult (used by FlattenerInterface)
    - ProcessingResult, WorkflowResult (used by Orchestrator)

SEE ALSO:
    - docs/COMPONENT_SPECIFICATIONS.md - Full interface specifications
    - components/source/ - Example source implementations
    - components/destination/ - Example destination implementations
    - components/converter/ - Example converter implementations
    - components/flattener/ - Example flattener implementations
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SourceFileInfo:
    """Information about a file from source"""
    path: Path
    version: str  # Commit hash, timestamp, or version ID
    version_date: datetime
    status: str  # 'added', 'modified', 'deleted'


@dataclass
class SourceSyncState:
    """Tracks synchronisation state"""
    last_processed_version: Optional[str]
    last_processed_date: Optional[datetime]


@dataclass
class DownloadResult:
    """Result from downloading a file"""
    success: bool
    source_path: str
    local_path: Path
    version: str
    errors: List[str] = field(default_factory=list)


@dataclass
class UploadResult:
    """Result from uploading files"""
    success: bool
    version: Optional[str]  # Commit hash or version created
    files_uploaded: List[Path]
    message: str
    errors: List[str] = field(default_factory=list)


@dataclass
class ConversionResult:
    """Result from conversion"""
    success: bool
    input_path: Path
    output_path: Optional[Path]  # None if no conversion performed
    conversion_performed: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class FlattenResult:
    """Result from flattening"""
    success: bool
    input_path: Path
    flat_root: Optional[Path]
    manifest_path: Optional[Path]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class ProcessingResult:
    """Result from processing a single file"""
    success: bool
    input_file: Path
    conversion_result: Optional[ConversionResult] = None
    flatten_result: Optional[FlattenResult] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    """Result of entire workflow"""
    files_processed: int
    files_succeeded: int
    files_failed: int
    processing_results: List[ProcessingResult]
    errors: List[str] = field(default_factory=list)


# ============================================================================
# Component Interfaces
# ============================================================================

class SourceInterface(ABC):
    """Interface for getting files to process"""

    def __init__(self, config: dict):
        """Initialize source with configuration"""
        self.config = config

    @abstractmethod
    def get_sync_state(self) -> SourceSyncState:
        """
        Get last synchronisation state.

        Reads state file from destination (written in previous run).
        Returns state with last_processed_version=None if first run.
        """
        pass

    @abstractmethod
    def get_changed_files(
        self,
        include_patterns: List[str],
        exclude_patterns: List[str],
        since_version: Optional[str],
        depth: int
    ) -> List[SourceFileInfo]:
        """
        Get files that have changed.

        Args:
            include_patterns: Glob patterns to include
            exclude_patterns: Glob patterns to exclude
            since_version: Get changes since this version (if None, use depth)
            depth: How many versions back if since_version is None
                   0 = return empty list
                   1 = only latest version
                   N = last N versions
        """
        pass

    @abstractmethod
    def download_file(
        self,
        source_path: str,
        version: str,
        local_dest: Path
    ) -> DownloadResult:
        """Download specific file at specific version"""
        pass

    @abstractmethod
    def get_current_version(self) -> str:
        """Get current version identifier of source"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return name of this source implementation"""
        pass


class DestinationInterface(ABC):
    """Interface for uploading processed results"""

    def __init__(self, config: dict):
        """Initialize destination with configuration"""
        self.config = config

    @abstractmethod
    def save_sync_state(self, state: SourceSyncState) -> None:
        """Save synchronisation state to destination"""
        pass

    @abstractmethod
    def upload_file(
        self,
        local_file: Path,
        remote_path: str,
        message: str
    ) -> UploadResult:
        """Upload single file"""
        pass

    @abstractmethod
    def upload_directory(
        self,
        local_dir: Path,
        remote_path: str,
        message: str
    ) -> UploadResult:
        """Upload entire directory"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return name of this destination implementation"""
        pass


class ConverterInterface(ABC):
    """Interface for Excel file conversion"""

    def __init__(self, config: dict):
        """Initialize converter with configuration"""
        self.config = config

    @abstractmethod
    def needs_conversion(self, file_path: Path) -> bool:
        """Determine if file needs conversion"""
        pass

    @abstractmethod
    def can_convert(self, file_path: Path) -> bool:
        """Check if this converter can handle the file"""
        pass

    @abstractmethod
    def convert(
        self,
        input_path: Path,
        output_dir: Optional[Path] = None
    ) -> ConversionResult:
        """Convert file to appropriate format"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return name of this converter implementation"""
        pass


class FlattenerInterface(ABC):
    """Interface for Excel flattening"""

    def __init__(self, config: dict):
        """Initialize flattener with configuration"""
        self.config = config

    @abstractmethod
    def flatten(
        self,
        excel_file: Path,
        origin_repo: Optional[str] = None,
        origin_path: Optional[str] = None,
        origin_commit: Optional[str] = None
    ) -> FlattenResult:
        """Flatten Excel file to text representation"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return name of this flattener implementation"""
        pass
