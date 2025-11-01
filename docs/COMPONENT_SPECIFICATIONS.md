# Excel Differ - Component Specifications

**Version:** 3.0
**Last Updated:** 2025-11-01
**Purpose:** Complete interface specifications for all components

---

## Overview

This document provides **complete specifications** for all component interfaces in Excel Differ. Use this document when:

- **Implementing a new component** (e.g., GitHub source, S3 destination)
- **Understanding component contracts** (what each method must do)
- **Writing tests** (what to verify)
- **Debugging** (what each component is responsible for)

---

## Table of Contents

1. [SourceInterface](#1-sourceinterface)
2. [DestinationInterface](#2-destinationinterface)
3. [ConverterInterface](#3-converterinterface)
4. [FlattenerInterface](#4-flattenerinterface)
5. [Orchestrator](#5-orchestrator)
6. [Data Classes](#6-data-classes)
7. [Configuration](#7-configuration)

---

## 1. SourceInterface

### Purpose

Get files to process from a source (Bitbucket, local folder, GitHub, S3, etc.)

### Interface Definition

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

class SourceInterface(ABC):
    """Interface for getting files to process"""

    def __init__(self, config: dict):
        """
        Initialize source with configuration.

        Args:
            config: Implementation-specific configuration dict
                   For Bitbucket: {url, branch, token, include_patterns, ...}
                   For local: {folder_path, include_patterns, ...}
        """
        self.config = config

    @abstractmethod
    def get_sync_state(self) -> SourceSyncState:
        """
        Get last synchronisation state from destination.

        Reads state from destination to know what was last processed.
        Note: This reads from DESTINATION, not source!

        Returns:
            SourceSyncState with:
            - last_processed_version: None if first run, else version ID
            - last_processed_date: When last processed

        Implementation Notes:
            - Bitbucket: Read .excel-differ-state.json from destination repo via API
            - Local: Read .excel-differ-state.json from destination folder
            - If file doesn't exist, return state with last_processed_version=None
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
            include_patterns: Glob patterns to include (e.g., '**/*.xlsx')
            exclude_patterns: Glob patterns to exclude (e.g., '**/archive/**')
            since_version: Get changes since this version. If None, use depth.
            depth: How many versions back if since_version is None
                   0 = return empty list (do nothing)
                   1 = only latest version
                   5 = last 5 versions

        Returns:
            List of SourceFileInfo objects for matching files

        Algorithm:
            1. Determine version range:
               - If since_version: since_version..current
               - Else if depth > 0: last N versions
               - Else (depth=0): return []

            2. For each version in range:
               - Get list of files changed in that version
               - Filter by include_patterns
               - Remove matches of exclude_patterns
               - Add to results (deduplicated by path)

            3. Return deduplicated list

        Implementation Notes:
            - Bitbucket: Use commits API + diffstat API
            - Local: Scan folder, check modification times
            - GitPython: Use git log + git diff
            - Pattern matching: Use fnmatch or glob syntax

        Example:
            include_patterns = ['**/*.xlsx', 'data/**/*.xlsm']
            exclude_patterns = ['**/archive/**']
            since_version = 'abc123'

            # Returns files matching patterns changed since commit abc123
        """
        pass

    @abstractmethod
    def download_file(
        self,
        source_path: str,
        version: str,
        local_dest: Path
    ) -> DownloadResult:
        """
        Download a specific file at a specific version.

        Args:
            source_path: Path to file in source (relative)
            version: Version identifier (commit hash, timestamp, etc.)
            local_dest: Where to save file locally

        Returns:
            DownloadResult with:
            - success: True if downloaded
            - source_path: Original path
            - local_path: Where saved
            - version: Version downloaded
            - errors: List of errors if failed

        Implementation Notes:
            - Bitbucket: GET /2.0/repositories/{workspace}/{repo}/src/{commit}/{path}
            - Local: Copy file from source folder
            - GitPython: git show {commit}:{path} > local_dest
            - Create parent directories if needed
            - Handle errors gracefully (file not found, network timeout, etc.)

        Example:
            result = source.download_file(
                source_path='data/sales.xlsx',
                version='abc123def',
                local_dest=Path('/tmp/sales.xlsx')
            )

            if result.success:
                print(f"Downloaded to {result.local_path}")
        """
        pass

    @abstractmethod
    def get_current_version(self) -> str:
        """
        Get current version identifier of source.

        Returns:
            Version string:
            - Bitbucket/Git: Current commit hash
            - Local folder: Current timestamp (ISO format)
            - S3: Latest version ID

        Implementation Notes:
            - Bitbucket: GET /2.0/repositories/{workspace}/{repo}/refs/branches/{branch}
            - Local: datetime.now().isoformat()
            - GitPython: git rev-parse HEAD

        Purpose:
            Used to update sync state after successful processing.
            Next run will process changes since this version.
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get name of this source implementation.

        Returns:
            Human-readable name (e.g., 'BitbucketSource', 'LocalFolderSource')

        Purpose:
            - Logging and debugging
            - Error messages
            - Component identification
        """
        pass
```

### Implementation Checklist

When implementing a new source:

- [ ] Implement `__init__(config: dict)` accepting config
- [ ] Implement `get_sync_state()` reading from destination
- [ ] Implement `get_changed_files()` with pattern filtering
- [ ] Implement `download_file()` with error handling
- [ ] Implement `get_current_version()` returning version ID
- [ ] Implement `get_name()` returning implementation name
- [ ] Write unit tests for each method
- [ ] Write integration tests with real data
- [ ] Document configuration options
- [ ] Handle authentication
- [ ] Handle errors gracefully
- [ ] Add logging

---

## 2. DestinationInterface

### Purpose

Upload processed results to a destination (Bitbucket, local folder, GitHub, S3, etc.)

### Interface Definition

```python
class DestinationInterface(ABC):
    """Interface for uploading processed results"""

    def __init__(self, config: dict):
        """
        Initialize destination with configuration.

        Args:
            config: Implementation-specific configuration dict
                   For Bitbucket: {url, branch, token, output_path, ...}
                   For local: {folder_path, ...}
        """
        self.config = config

    @abstractmethod
    def save_sync_state(self, state: SourceSyncState) -> None:
        """
        Save synchronisation state.

        Writes .excel-differ-state.json to destination.

        Args:
            state: SourceSyncState with last_processed_version and date

        State File Format:
            {
              "last_processed_version": "abc123def456",
              "last_processed_date": "2025-11-01T14:30:00Z"
            }

        Implementation Notes:
            - Bitbucket: Upload file via POST /2.0/repositories/.../src
            - Local: Write file to destination folder
            - GitPython: Add, commit, push state file
            - Overwrite existing state file
            - Commit with message like "Update sync state"

        Error Handling:
            - Raise exception if save fails
            - Log errors

        Example:
            state = SourceSyncState(
                last_processed_version='abc123',
                last_processed_date=datetime.now()
            )
            destination.save_sync_state(state)
        """
        pass

    @abstractmethod
    def upload_file(
        self,
        local_file: Path,
        remote_path: str,
        message: str
    ) -> UploadResult:
        """
        Upload a single file.

        Args:
            local_file: Local file to upload
            remote_path: Where to put it in destination (relative path)
            message: Commit message or description

        Returns:
            UploadResult with:
            - success: True if uploaded
            - version: Commit hash or version ID created
            - files_uploaded: List of files uploaded
            - errors: List of errors if failed

        Implementation Notes:
            - Bitbucket: POST /2.0/repositories/.../src with single file
            - Local: Copy file to destination folder
            - GitPython: Add, commit, push file
            - Create parent directories if needed
            - Overwrite if file exists

        Example:
            result = destination.upload_file(
                local_file=Path('/tmp/manifest.json'),
                remote_path='flattened/workbook-flat-123/manifest.json',
                message='Add manifest for workbook'
            )
        """
        pass

    @abstractmethod
    def upload_directory(
        self,
        local_dir: Path,
        remote_path: str,
        message: str
    ) -> UploadResult:
        """
        Upload entire directory (recursively).

        Args:
            local_dir: Local directory to upload
            remote_path: Where to put it in destination
            message: Commit message

        Returns:
            UploadResult with success, version, files_uploaded, errors

        Implementation Notes:
            - Bitbucket: POST /2.0/repositories/.../src with multipart form
                       Upload all files in single API call
            - Local: Copy directory tree to destination
            - GitPython: Add directory, commit, push
            - Preserve directory structure
            - Upload all files including subdirectories

        Algorithm:
            1. Scan local_dir for all files (recursive)
            2. For each file:
               - Calculate relative path
               - Construct remote path
               - Add to upload batch
            3. Upload all files (single commit/operation)
            4. Return result

        Example:
            result = destination.upload_directory(
                local_dir=Path('/tmp/workbook-flat-20251101T140000'),
                remote_path='flattened/workbook-flat-20251101T140000',
                message='Flatten workbook.xlsx'
            )

            # Uploads entire directory tree:
            # flattened/workbook-flat-20251101T140000/
            #   manifest.json
            #   metadata.txt
            #   sheets/
            #     Sheet1/
            #       formulas-by-row.txt
            #       ...
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get name of this destination implementation.

        Returns:
            Human-readable name (e.g., 'BitbucketDestination', 'LocalFolderDestination')
        """
        pass
```

### Implementation Checklist

When implementing a new destination:

- [ ] Implement `__init__(config: dict)` accepting config
- [ ] Implement `save_sync_state()` writing state file
- [ ] Implement `upload_file()` with error handling
- [ ] Implement `upload_directory()` handling recursive uploads
- [ ] Implement `get_name()` returning implementation name
- [ ] Write unit tests for each method
- [ ] Write integration tests with real data
- [ ] Document configuration options
- [ ] Handle authentication
- [ ] Handle errors gracefully (permissions, conflicts, etc.)
- [ ] Add logging

---

## 3. ConverterInterface

### Purpose

Convert Excel file formats (primarily .xlsb → .xlsm)

### Interface Definition

```python
class ConverterInterface(ABC):
    """Interface for Excel file conversion"""

    def __init__(self, config: dict):
        """
        Initialize converter with configuration.

        Args:
            config: Implementation-specific configuration
                   For LibreOffice: {tool_path, timeout, ...}
                   For NoOp: {}
        """
        self.config = config

    @abstractmethod
    def needs_conversion(self, file_path: Path) -> bool:
        """
        Determine if file needs conversion.

        Args:
            file_path: Path to Excel file

        Returns:
            True if conversion is needed, False otherwise

        Conversion Logic:
            - .xlsb → True (needs conversion to .xlsm to preserve macros)
            - .xls → Maybe (implementation-specific, platform-dependent)
            - .xlsx, .xlsm → False (already in modern format)

        Implementation Notes:
            - Check file extension (file_path.suffix)
            - May also check file content/headers
            - NoOpConverter: Always returns False

        Example:
            if converter.needs_conversion(Path('file.xlsb')):
                # Conversion required
        """
        pass

    @abstractmethod
    def can_convert(self, file_path: Path) -> bool:
        """
        Check if this converter can handle the file.

        Args:
            file_path: Path to Excel file

        Returns:
            True if this converter can convert the file, False otherwise

        Checks:
            - Platform compatibility (Windows COM vs LibreOffice)
            - Required dependencies available
            - File format supported

        Implementation Notes:
            - WindowsExcelConverter: Check platform.system() == 'Windows'
            - LibreOfficeConverter: Check LibreOffice binary exists
            - NoOpConverter: Always returns True (can "handle" by doing nothing)

        Purpose:
            Allows orchestrator to detect mismatches:
            "File needs conversion but NoOpConverter cannot convert it"

        Example:
            if not converter.can_convert(file_path):
                print(f"{converter.get_name()} cannot handle this file")
        """
        pass

    @abstractmethod
    def convert(
        self,
        input_path: Path,
        output_dir: Optional[Path] = None
    ) -> ConversionResult:
        """
        Convert file to appropriate format.

        Args:
            input_path: Source Excel file
            output_dir: Where to save converted file. If None, use same directory.

        Returns:
            ConversionResult with:
            - success: True if conversion succeeded
            - input_path: Original file
            - output_path: Converted file (None if no conversion)
            - conversion_performed: True if actually converted
            - warnings: List of warnings
            - errors: List of errors if failed

        Output Format Decision:
            - .xlsb → .xlsm (preserve macros)
            - .xls → .xlsx (if no macros) or .xlsm (if macros detected)

        Implementation Notes:
            - Create output file with appropriate extension
            - WindowsExcelConverter: Use win32com to open and save
            - LibreOfficeConverter: Use subprocess with headless mode
            - Handle timeouts gracefully
            - Clean up temp files

        Error Handling:
            - If conversion fails: success=False, errors populated
            - If timeout: Add to errors
            - If file corrupt: Add to errors

        Example:
            result = converter.convert(
                input_path=Path('workbook.xlsb'),
                output_dir=Path('/tmp/converted')
            )

            if result.success:
                # Use result.output_path for flattening
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get name of this converter implementation.

        Returns:
            Human-readable name (e.g., 'WindowsExcelConverter', 'NoOpConverter')
        """
        pass
```

### NoOpConverter Special Case

```python
class NoOpConverter(ConverterInterface):
    """
    Explicit no-operation converter.

    Use when you don't want any conversion (most common case).
    Makes intent clear: "I explicitly don't want conversion"
    vs passing None which is ambiguous.
    """

    def needs_conversion(self, file_path: Path) -> bool:
        return False  # Never needs conversion

    def can_convert(self, file_path: Path) -> bool:
        return True  # Can "handle" anything by doing nothing

    def convert(self, input_path: Path, output_dir: Optional[Path] = None) -> ConversionResult:
        return ConversionResult(
            success=True,
            input_path=input_path,
            output_path=None,
            conversion_performed=False,
            warnings=[],
            errors=[]
        )

    def get_name(self) -> str:
        return "NoOpConverter"
```

### Implementation Checklist

- [ ] Implement `__init__(config: dict)` accepting config
- [ ] Implement `needs_conversion()` checking file type
- [ ] Implement `can_convert()` checking platform/dependencies
- [ ] Implement `convert()` with timeout handling
- [ ] Implement `get_name()` returning implementation name
- [ ] Write unit tests for each method
- [ ] Write integration tests with real Excel files
- [ ] Document platform requirements
- [ ] Handle conversion timeouts
- [ ] Clean up temporary files
- [ ] Add logging

---

## 4. FlattenerInterface

### Purpose

Flatten Excel workbook to deterministic text representation

### Interface Definition

```python
class FlattenerInterface(ABC):
    """Interface for Excel flattening"""

    def __init__(self, config: dict):
        """
        Initialize flattener with configuration.

        Args:
            config: Flattener configuration:
                   {
                     'include_computed': bool,
                     'include_literal': bool,
                     'include_formats': bool,
                     'timeout': int,
                     'output_dir': Path
                   }
        """
        self.config = config

    @abstractmethod
    def flatten(
        self,
        excel_file: Path,
        origin_repo: Optional[str] = None,
        origin_path: Optional[str] = None,
        origin_commit: Optional[str] = None
    ) -> FlattenResult:
        """
        Flatten Excel file to text representation.

        Args:
            excel_file: Path to Excel file (.xlsx or .xlsm)
            origin_repo: Source repository URL (for traceability)
            origin_path: Original file path in repo
            origin_commit: Commit hash where file came from

        Returns:
            FlattenResult with:
            - success: True if flattening succeeded
            - input_path: Original Excel file
            - flat_root: Path to flat directory (timestamped)
            - manifest_path: Path to manifest.json
            - warnings: List of warnings (non-fatal issues)
            - errors: List of errors if failed

        Output Structure:
            workbook-flat-20251101T140000-a3f5c8d1/
            ├── manifest.json
            ├── metadata.txt
            ├── workbook-structure.txt
            ├── named-ranges.txt
            ├── tables.txt
            ├── charts.txt
            ├── sheets/
            │   ├── Sheet1/
            │   │   ├── formulas-by-row.txt
            │   │   ├── formulas-by-column.txt
            │   │   ├── literal-values.txt
            │   │   ├── computed-values.txt (optional)
            │   │   └── formats.txt (optional)
            │   └── Sheet2/
            │       └── ...
            └── vba/
                ├── vba-summary.txt
                └── Module1.bas

        Manifest Format:
            {
              "workbook_filename": "budget.xlsx",
              "original_sha256": "a3f5c8d1...",
              "extracted_at": "2025-11-01T14:00:00Z",
              "extractor_version": "2.1.0",
              "origin": {
                "origin_repo": "https://bitbucket.org/org/repo",
                "origin_path": "data/budget.xlsx",
                "origin_commit": "abc123"
              },
              "sheets": [...],
              "files": [...],
              "warnings": [...]
            }

        Error Handling:
            - If timeout: success=False, timeout error
            - If corrupt file: success=False, parse error
            - If partial extraction: success=True, warnings populated
            - Continue processing on non-fatal errors

        Implementation Notes:
            - See FLATTENER_SPECS.md for complete details
            - Use openpyxl for parsing
            - Extract in deterministic order
            - Normalize text encoding (UTF-8), line endings (LF)
            - Include origin metadata in manifest

        Example:
            result = flattener.flatten(
                excel_file=Path('/tmp/budget.xlsx'),
                origin_repo='https://bitbucket.org/org/repo',
                origin_path='finance/budget.xlsx',
                origin_commit='abc123def'
            )

            if result.success:
                print(f"Flattened to {result.flat_root}")
                print(f"Warnings: {result.warnings}")
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get name of this flattener implementation.

        Returns:
            Human-readable name (e.g., 'OpenpyxlFlattener')
        """
        pass
```

### Implementation Checklist

- [ ] Implement `__init__(config: dict)` accepting config
- [ ] Implement `flatten()` with all extraction modules
- [ ] Handle timeout gracefully (thread-based)
- [ ] Generate manifest with origin metadata
- [ ] Create deterministic output (same input = same output)
- [ ] Normalize text (UTF-8, LF line endings)
- [ ] Extract formulas, values, VBA, charts, tables, metadata
- [ ] Implement `get_name()` returning implementation name
- [ ] Write comprehensive unit tests
- [ ] Write integration tests with real Excel files
- [ ] Document configuration options
- [ ] Handle errors gracefully
- [ ] Add detailed logging

---

## 5. Orchestrator

### Purpose

Coordinate the overall workflow (not an interface, but key component)

### Class Definition

```python
class Orchestrator:
    """Coordinates excel-differ workflow"""

    def __init__(
        self,
        source: SourceInterface,
        destination: DestinationInterface,
        converter: ConverterInterface,
        flattener: FlattenerInterface,
        config: ExcelDifferConfig
    ):
        """
        Initialize orchestrator with all components.

        All components are REQUIRED. Use NoOp implementations to disable.

        Args:
            source: Source implementation (where to get files)
            destination: Destination implementation (where to upload results)
            converter: Converter implementation (how to convert)
            flattener: Flattener implementation (how to flatten)
            config: Overall configuration

        Example:
            orchestrator = Orchestrator(
                source=BitbucketSource(config.source.config),
                destination=BitbucketDestination(config.destination.config),
                converter=NoOpConverter(config.converter.config),
                flattener=OpenpyxlFlattener(config.flattener.config),
                config=config
            )
        """
        self.source = source
        self.destination = destination
        self.converter = converter
        self.flattener = flattener
        self.config = config

    def run(self) -> WorkflowResult:
        """
        Execute the workflow.

        Returns:
            WorkflowResult with:
            - files_processed: Total files attempted
            - files_succeeded: Successfully processed
            - files_failed: Failed
            - processing_results: List of per-file results
            - errors: Overall errors

        Workflow Steps:
            1. Get sync state (from destination)
            2. Get changed files (from source)
            3. For each file:
               a. Download file
               b. Convert if needed
               c. Flatten
               d. Upload flat directory
            4. Update sync state (to destination)
            5. Return summary

        Error Handling:
            - Continue processing other files if one fails
            - Collect all errors
            - Report summary at end
            - Update sync state only if at least one file succeeded

        Example:
            result = orchestrator.run()
            print(f"Processed: {result.files_processed}")
            print(f"Succeeded: {result.files_succeeded}")
            print(f"Failed: {result.files_failed}")
            for error in result.errors:
                print(f"Error: {error}")
        """
        pass
```

---

## 6. Data Classes

### SourceFileInfo

```python
@dataclass
class SourceFileInfo:
    """Information about a file from source"""
    path: Path                # Relative path in source
    version: str             # Commit hash, timestamp, or version ID
    version_date: datetime   # When this version was created
    status: str              # 'added', 'modified', 'deleted'
```

### SourceSyncState

```python
@dataclass
class SourceSyncState:
    """Synchronisation state"""
    last_processed_version: Optional[str]  # Last version processed
    last_processed_date: Optional[datetime]  # When processed
```

### DownloadResult

```python
@dataclass
class DownloadResult:
    """Result from downloading a file"""
    success: bool
    source_path: str
    local_path: Path
    version: str
    errors: List[str]
```

### UploadResult

```python
@dataclass
class UploadResult:
    """Result from uploading files"""
    success: bool
    version: Optional[str]      # Commit hash or version created
    files_uploaded: List[Path]
    errors: List[str]
```

### ConversionResult

```python
@dataclass
class ConversionResult:
    """Result from conversion"""
    success: bool
    input_path: Path
    output_path: Optional[Path]  # None if no conversion performed
    conversion_performed: bool
    warnings: List[str]
    errors: List[str]
```

### FlattenResult

```python
@dataclass
class FlattenResult:
    """Result from flattening"""
    success: bool
    input_path: Path
    flat_root: Optional[Path]
    manifest_path: Optional[Path]
    warnings: List[str]
    errors: List[str]
```

### WorkflowResult

```python
@dataclass
class WorkflowResult:
    """Result of entire workflow"""
    files_processed: int
    files_succeeded: int
    files_failed: int
    processing_results: List[ProcessingResult]
    errors: List[str]
```

---

## 7. Configuration

### ExcelDifferConfig

```python
@dataclass
class RepoConfig:
    """Repository configuration"""
    url: str
    branch: str
    token: str
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    output_path: str = "/"
    depth: int = 1

@dataclass
class SyncConfig:
    """Sync behaviour"""
    depth: int = 1

@dataclass
class ComponentConfig:
    """Generic component configuration"""
    implementation: str
    config: dict = field(default_factory=dict)

@dataclass
class ExcelDifferConfig:
    """Main configuration"""
    source: RepoConfig
    destination: RepoConfig
    sync: SyncConfig
    converter: ComponentConfig
    flattener: ComponentConfig
```

### Configuration Loading

```python
def load_config(config_path: Path) -> ExcelDifferConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML config file

    Returns:
        ExcelDifferConfig object

    Processing:
        1. Load YAML file
        2. Resolve environment variables (${VAR})
        3. Validate required fields
        4. Create config objects
        5. Return ExcelDifferConfig

    Example YAML:
        source:
          implementation: bitbucket
          config:
            url: https://bitbucket.org/org/repo
            branch: main
            token: ${BITBUCKET_TOKEN}
            include_patterns:
              - "**/*.xlsx"
            depth: 1

        destination:
          implementation: bitbucket
          config:
            url: https://bitbucket.org/org/repo
            branch: main
            token: ${BITBUCKET_TOKEN}
            output_path: flattened/

        sync:
          depth: 1

        converter:
          implementation: noop
          config: {}

        flattener:
          implementation: openpyxl
          config:
            include_computed: false
            timeout: 900
    """
    pass
```

---

## 8. Quick Reference: Adding a New Component

### Step 1: Create Implementation Class

```python
# components/source/my_new_source.py

from components.core.interfaces import SourceInterface

class MyNewSource(SourceInterface):
    def __init__(self, config: dict):
        super().__init__(config)
        # Initialize your specific setup

    def get_sync_state(self) -> SourceSyncState:
        # Implement
        pass

    def get_changed_files(self, ...) -> List[SourceFileInfo]:
        # Implement
        pass

    def download_file(self, ...) -> DownloadResult:
        # Implement
        pass

    def get_current_version(self) -> str:
        # Implement
        pass

    def get_name(self) -> str:
        return "MyNewSource"
```

### Step 2: Register in Plugin Registry

```python
# components/core/plugin_registry.py

from components.source.my_new_source import MyNewSource

registry.register_source('mynew', MyNewSource)
```

### Step 3: Use in Configuration

```yaml
# config/excel-differ.yaml

source:
  implementation: mynew
  config:
    # Your implementation-specific config
    api_key: ${MY_API_KEY}
    region: us-west-1
```

### Step 4: Test

```python
# tests/test_my_new_source.py

def test_my_new_source():
    config = {'api_key': 'test', 'region': 'us-west-1'}
    source = MyNewSource(config)

    # Test each method
    assert source.get_name() == "MyNewSource"
    # ... more tests
```

---

## References

- [ARCHITECTURE_V3.md](ARCHITECTURE_V3.md) - Overall architecture
- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Project status
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment instructions
- [FLATTENER_SPECS.md](FLATTENER_SPECS.md) - Flattener details

---

**END OF COMPONENT SPECIFICATIONS**
