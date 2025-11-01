# Excel Differ - Plugin Architecture (V3)

**Version:** 3.0
**Date:** 2025-11-01
**Status:** Design Document

---

## 1. Overview

Excel Differ is a **modular, plugin-based system** for converting Excel workbooks into version-control-friendly text representations. The architecture emphasises:

- **Separation of Concerns:** Distinct components for getting files, converting, flattening, and uploading
- **Pluggable Implementations:** Interface-based design allows multiple implementations per component
- **Configuration-Driven:** YAML configuration determines which implementations to use
- **Loose Coupling:** Components communicate only through interfaces
- **Independent Development:** Each component can be developed, tested, and deployed independently

---

## 2. Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                          │
│            Coordinates overall workflow                     │
└──────────┬──────────────┬──────────────┬──────────────┬────┘
           │              │              │              │
           ▼              ▼              ▼              ▼
     ┌─────────┐    ┌───────────┐  ┌──────────┐  ┌─────────────┐
     │ SOURCE  │    │ CONVERTER │  │FLATTENER │  │ DESTINATION │
     └─────────┘    └───────────┘  └──────────┘  └─────────────┘
          │                                              │
          │                                              │
   ┌──────┴──────┐                              ┌────────┴────────┐
   ▼             ▼                              ▼                 ▼
Bitbucket    Local Folder                  Bitbucket        Local Folder
GitHub       S3 Bucket                     GitHub           S3 Bucket
GitPython    HTTP                          GitPython        Azure Blob
```

### Key Principle: Interface-Based Pluggability

Each component type has:
1. **An interface** (abstract base class) defining required methods
2. **Multiple implementations** of that interface
3. **Configuration** specifying which implementation to use

---

## 3. Component Interfaces

### 3.1 Source Interface

**Purpose:** Get files to process

**Implementation Examples:**
- `BitbucketSource` - Get files from Bitbucket via API
- `GitHubSource` - Get files from GitHub via API
- `LocalFolderSource` - Get files from local filesystem
- `GitPythonSource` - Get files from local git repository
- `S3Source` - Get files from AWS S3

**Key Methods:**
```python
class SourceInterface(ABC):
    def __init__(self, config: dict)
    def get_sync_state(self) -> SourceSyncState
    def get_changed_files(...) -> List[SourceFileInfo]
    def download_file(...) -> DownloadResult
    def get_current_version(self) -> str
    def get_name(self) -> str
```

**Responsibilities:**
- Track synchronisation state (what was last processed)
- Detect changed files since last sync
- Download files at specific versions
- Support include/exclude patterns for filtering
- Handle authentication

---

### 3.2 Destination Interface

**Purpose:** Upload processed results

**Implementation Examples:**
- `BitbucketDestination` - Upload to Bitbucket via API
- `GitHubDestination` - Upload to GitHub via API
- `LocalFolderDestination` - Save to local filesystem
- `GitPythonDestination` - Commit to local git repository
- `S3Destination` - Upload to AWS S3

**Key Methods:**
```python
class DestinationInterface(ABC):
    def __init__(self, config: dict)
    def save_sync_state(state: SourceSyncState) -> None
    def upload_file(...) -> UploadResult
    def upload_directory(...) -> UploadResult
    def get_name(self) -> str
```

**Responsibilities:**
- Save synchronisation state
- Upload single files
- Upload entire directories
- Handle authentication
- Create commits/versions

---

### 3.3 Converter Interface

**Purpose:** Convert Excel file formats

**Implementation Examples:**
- `NoOpConverter` - Explicit no-conversion (most common)
- `WindowsExcelConverter` - Use Windows COM automation
- `LibreOfficeConverter` - Use LibreOffice headless

**Key Methods:**
```python
class ConverterInterface(ABC):
    def __init__(self, config: dict)
    def needs_conversion(file_path: Path) -> bool
    def can_convert(file_path: Path) -> bool
    def convert(...) -> ConversionResult
    def get_name(self) -> str
```

**Responsibilities:**
- Determine if conversion is needed (.xlsb → .xlsm)
- Check if this converter can handle the file (platform check)
- Perform conversion
- Report success/failure

---

### 3.4 Flattener Interface

**Purpose:** Flatten Excel to text representation

**Implementation Examples:**
- `OpenpyxlFlattener` - Use openpyxl library
- `NoOpFlattener` - Explicit no-flattening (acts as file copier)
- `PandasFlattener` - Use pandas library
- `XlrdFlattener` - Use xlrd library

**Key Methods:**
```python
class FlattenerInterface(ABC):
    def __init__(self, config: dict)
    def flatten(...) -> FlattenResult
    def get_name(self) -> str
```

**Responsibilities:**
- Parse Excel file
- Extract all content (formulas, values, VBA, metadata)
- Generate structured text files
- Create manifest
- Handle errors gracefully

---

### 3.5 Orchestrator

**Purpose:** Coordinate the workflow

**Key Methods:**
```python
class Orchestrator:
    def __init__(
        self,
        source: SourceInterface,
        destination: DestinationInterface,
        converter: ConverterInterface,
        flattener: FlattenerInterface,
        config: ExcelDifferConfig
    )
    def run(self) -> WorkflowResult
```

**Workflow:**
```
1. Get sync state (from destination)
2. Get changed files (from source)
3. For each file:
   a. Download file (from source)
   b. Convert if needed (converter)
   c. Flatten (flattener)
   d. Upload result (to destination)
4. Update sync state (to destination)
5. Return summary
```

---

## 4. Component Interaction Flow

### 4.1 Normal Processing Flow

```
┌─────────────┐
│Orchestrator │
└──────┬──────┘
       │
       │ 1. get_sync_state()
       │    Reads state file written by Destination in previous run
       ├─────────────────────────────┐
       │                             ▼
       │                      ┌────────────┐
       │                      │   SOURCE   │
       │                      └────────────┘
       │                             │
       │ 2. Return: last_processed_version
       │◄────────────────────────────┘
       │
       │ 3. get_changed_files(since_version, depth, patterns)
       ├─────────────────────────────┐
       │                             ▼
       │                      ┌────────────┐
       │                      │   SOURCE   │
       │                      └────────────┘
       │                             │
       │ 4. Return: list of changed files
       │◄────────────────────────────┘
       │
       │ For each file:
       │   5. download_file(path, version)
       ├─────────────────────────────┐
       │                             ▼
       │                      ┌────────────┐
       │                      │   SOURCE   │
       │                      └────────────┘
       │                             │
       │ 6. Return: local file path
       │◄────────────────────────────┘
       │
       │ 7. needs_conversion(file)?
       ├─────────────────────┐
       │                     ▼
       │              ┌────────────┐
       │              │  CONVERTER │
       │              └────────────┘
       │                     │
       │ 8. Return: true/false
       │◄────────────────────┘
       │
       │ If needs conversion:
       │ 9. convert(file)
       ├─────────────────────┐
       │                     ▼
       │              ┌────────────┐
       │              │  CONVERTER │
       │              └────────────┘
       │                     │
       │ 10. Return: converted file
       │◄────────────────────┘
       │
       │ 11. flatten(file)
       ├─────────────────────┐
       │                     ▼
       │              ┌────────────┐
       │              │  FLATTENER │
       │              └────────────┘
       │                     │
       │ 12. Return: flat directory (or original file if NoOpFlattener)
       │◄────────────────────┘
       │
       │ 13. upload_directory(flat_dir, remote_path)
       ├──────────────────────────────────────────────────┐
       │                                                   ▼
       │                                          ┌─────────────────┐
       │                                          │  DESTINATION    │
       │                                          └─────────────────┘
       │                                                   │
       │ 14. Return: upload result ────────────────────────┘
       │
       │ 15. save_sync_state(new_state with current_version)
       ├──────────────────────────────────────────────────┐
       │                                                   ▼
       │                                          ┌─────────────────┐
       │                                          │  DESTINATION    │
       │                                          │ (writes state)  │
       │                                          └─────────────────┘
       │                                                   │
       │ 16. State saved ──────────────────────────────────┘
       │
       ▼
   Return summary
```

**Note:** `get_current_version()` is called internally by the orchestrator to populate the sync state before saving it. The current version comes from the source's latest state after processing.

---

## 5. Configuration System

### 5.1 Configuration File Structure

```yaml
# config/excel-differ.yaml

source:
  implementation: bitbucket  # Which Source implementation to use
  config:                    # Implementation-specific config
    url: https://bitbucket.org/workspace/repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    include_patterns:
      - "data/**/*.xlsx"
    exclude_patterns:
      - "**/archive/**"
    depth: 1  # How many commits back if no state (source-specific)

destination:
  implementation: bitbucket  # Which Destination implementation to use
  config:
    url: https://bitbucket.org/workspace/repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    output_path: flattened/

converter:
  implementation: noop  # Which Converter implementation to use
  config: {}

flattener:
  implementation: openpyxl  # Which Flattener implementation to use
  config:
    include_computed: false
    include_literal: true
    timeout: 900
```

**See [config/examples/](../config/examples/) for complete configuration examples for different scenarios.**

### 5.2 Configuration Loading

```python
# Load config from YAML
config = load_config('config/excel-differ.yaml')

# Create component instances based on config
source = create_source(config.source)
destination = create_destination(config.destination)
converter = create_converter(config.converter)
flattener = create_flattener(config.flattener)

# Create orchestrator with all components
orchestrator = Orchestrator(
    source=source,
    destination=destination,
    converter=converter,
    flattener=flattener,
    config=config
)

# Run
result = orchestrator.run()
```

---

## 6. Synchronisation Strategy

### 6.1 Sync State File

**Location:** Stored in destination repository as `.excel-differ-state.json`

**Format:**
```json
{
  "last_processed_version": "abc123def456",
  "last_processed_date": "2025-11-01T14:30:00Z"
}
```

**Interpretation:**
- `last_processed_version`: Last commit hash (git) or timestamp (local) processed
- `last_processed_date`: When it was processed (for debugging)

### 6.2 Sync Behaviour

**On First Run (no state file):**
- Use `depth` parameter from config
- `depth=0`: Do nothing, wait for explicit trigger
- `depth=1`: Process only latest version (commit/files)
- `depth=5`: Process last 5 versions

**On Subsequent Runs (state file exists):**
- Use `last_processed_version` as starting point
- Get all changes since that version
- `depth` parameter is ignored

**State Update:**
- After successfully processing and uploading all files
- Update state file with current version
- Commit state file to destination

---

## 7. Pattern Matching

### 7.1 Include Patterns

Patterns specify which files to process:

```yaml
include_patterns:
  - "**/*.xlsx"           # All .xlsx files anywhere
  - "data/**/*.xlsm"      # All .xlsm under data/ and subdirs
  - "reports/*.xlsx"      # .xlsx only in reports/ (not subdirs)
  - "quarterly/**"        # All files under quarterly/ and subdirs
```

### 7.2 Exclude Patterns

Patterns specify which files to skip (applied after includes):

```yaml
exclude_patterns:
  - "**/archive/**"       # Exclude archive folders anywhere
  - "**/temp/**"          # Exclude temp folders
  - "**/.~lock.*"         # Exclude LibreOffice lock files
  - "**/~$*"              # Exclude Excel temp files
  - "**/backup_*"         # Exclude backup files
```

### 7.3 Pattern Evaluation

```python
# For each file in source:
1. Check if matches ANY include pattern
2. If yes, check if matches ANY exclude pattern
3. If matches include AND NOT exclude: PROCESS
4. Otherwise: SKIP
```

**Examples:**
```
File: "data/2024/sales.xlsx"
  Include match: "data/**/*.xlsm" ❌
  Include match: "**/*.xlsx" ✓
  Exclude match: "**/archive/**" ❌
  Result: PROCESS ✓

File: "data/archive/old.xlsx"
  Include match: "**/*.xlsx" ✓
  Exclude match: "**/archive/**" ✓
  Result: SKIP (excluded)

File: "reports/~$summary.xlsx"
  Include match: "**/*.xlsx" ✓
  Exclude match: "**/~$*" ✓
  Result: SKIP (excluded)
```

---

## 8. Error Handling Strategy

### 8.1 Error Categories and Responses

| Error Type | Examples | Orchestrator Response |
|------------|----------|----------------------|
| **Authentication** | Invalid token, expired credentials | STOP: Cannot proceed |
| **Network** | Connection timeout, API unavailable | RETRY: Exponential backoff |
| **File Download** | File not found at version, corrupt download | SKIP file, continue others |
| **Conversion** | Converter can't handle file, timeout | SKIP file, log warning |
| **Flattening** | Corrupt Excel, timeout, unsupported feature | SKIP file, log error |
| **Upload** | Insufficient permissions, conflict | RETRY: Up to 3 times |

### 8.2 Error Collection

```python
# Orchestrator collects all errors
results = {
    'files_processed': 10,
    'files_succeeded': 8,
    'files_failed': 2,
    'errors': [
        {
            'file': 'data/broken.xlsx',
            'stage': 'flattening',
            'error': 'Timeout after 900 seconds'
        },
        {
            'file': 'reports/old.xlsb',
            'stage': 'conversion',
            'error': 'NoOpConverter cannot convert .xlsb files'
        }
    ]
}
```

---

## 9. Implementation-Specific Behaviour

### 9.1 Bitbucket Source/Destination

**Authentication:**
- Uses Bitbucket App Passwords
- Format: `token: ${BITBUCKET_TOKEN}` (reads from .env)

**API Endpoints Used:**
- `GET /2.0/repositories/{workspace}/{repo}/commits/{branch}` - Get commits
- `GET /2.0/repositories/{workspace}/{repo}/diffstat/{commit}` - Get changed files
- `GET /2.0/repositories/{workspace}/{repo}/src/{commit}/{path}` - Download file
- `POST /2.0/repositories/{workspace}/{repo}/src` - Upload files

**Version Tracking:**
- Version = commit hash
- Sync state tracks last commit processed

**Change Detection:**
- Uses commit history and diffstat API
- Filters by file patterns

### 9.2 Local Folder Source/Destination

**Authentication:**
- None required (local filesystem)

**File Operations:**
- Copy files to/from directories
- Read/write sync state to `.excel-differ-state.json` in folder

**Version Tracking:**
- Version = file modification timestamp (ISO format)
- Tracks most recent modification time

**Change Detection:**
- Scans folder for files matching patterns
- Compares modification times with last sync

### 9.3 GitPython Source/Destination (Future)

**Authentication:**
- Uses git credentials (SSH keys or HTTPS tokens)

**Git Operations:**
- Clone repository to local workspace
- Use GitPython library for git operations
- `git log` for commits, `git diff` for changes
- `git add`, `git commit`, `git push` for uploads

**Version Tracking:**
- Version = commit hash
- Same as Bitbucket but using local git

**Change Detection:**
- Local git log and diff operations

---

## 10. Directory Structure

```
excel-differ/
├── components/
│   ├── core/                        # Core interfaces and registry
│   │   ├── __init__.py
│   │   ├── interfaces.py            # All interface definitions
│   │   ├── config.py                # Configuration data classes
│   │   ├── plugin_registry.py      # Component registration
│   │   └── config_loader.py         # YAML config loading
│   │
│   ├── source/                      # Source implementations
│   │   ├── __init__.py
│   │   ├── bitbucket_source.py
│   │   ├── local_folder_source.py
│   │   ├── github_source.py         # Future
│   │   └── gitpython_source.py      # Future
│   │
│   ├── destination/                 # Destination implementations
│   │   ├── __init__.py
│   │   ├── bitbucket_destination.py
│   │   ├── local_folder_destination.py
│   │   ├── github_destination.py    # Future
│   │   └── gitpython_destination.py # Future
│   │
│   ├── converter/                   # Converter implementations
│   │   ├── __init__.py
│   │   ├── noop_converter.py
│   │   ├── windows_excel_converter.py
│   │   └── libreoffice_converter.py
│   │
│   ├── flattener/                   # Flattener implementation
│   │   ├── src/
│   │   │   ├── flattener.py         # Existing implementation
│   │   │   └── flattener_plugin.py  # Interface wrapper
│   │   ├── tests/
│   │   ├── docs/
│   │   └── README.md
│   │
│   └── orchestrator/                # Orchestrator
│       ├── __init__.py
│       ├── orchestrator.py
│       └── workflow.py
│
├── config/                          # User configuration
│   └── excel-differ.yaml
│
├── docs/                            # Documentation
│   ├── ARCHITECTURE_V3.md           # This file
│   ├── COMPONENT_SPECIFICATIONS.md  # Detailed component specs
│   ├── PROJECT_PLAN.md              # Project status and plan
│   ├── DEPLOYMENT_GUIDE.md          # Deployment instructions
│   └── FLATTENER_SPECS.md           # Flattener specifications
│
├── .env                             # Secrets (git-ignored)
├── main.py                          # Entry point
├── requirements.txt                 # Python dependencies
└── README.md                        # Project overview
```

---

## 11. Testing Strategy

### 11.1 Interface Compliance Tests

Every implementation must pass interface compliance tests:

```python
def test_source_interface_compliance(source_implementation):
    """Test that implementation follows SourceInterface"""
    assert hasattr(source_implementation, 'get_sync_state')
    assert hasattr(source_implementation, 'get_changed_files')
    assert hasattr(source_implementation, 'download_file')
    assert hasattr(source_implementation, 'get_current_version')
    assert hasattr(source_implementation, 'get_name')
```

### 11.2 Mock Implementations for Testing

```python
class MockSource(SourceInterface):
    """Mock source for testing orchestrator"""
    def __init__(self, config: dict):
        self.files_to_return = config.get('mock_files', [])

    def get_changed_files(self, ...):
        return self.files_to_return
```

### 11.3 Integration Tests

```python
def test_bitbucket_to_local_workflow():
    """Test full workflow: Bitbucket source → Local destination"""
    source = BitbucketSource(config=...)
    destination = LocalFolderDestination(config=...)
    converter = NoOpConverter(config={})
    flattener = OpenpyxlFlattener(config=...)

    orchestrator = Orchestrator(source, destination, converter, flattener, config)
    result = orchestrator.run()

    assert result.files_succeeded > 0
```

---

## 12. Key Design Decisions

### Decision 1: Source and Destination Separation
**Date:** 2025-11-01
**Rationale:** "Getting files" and "uploading results" are fundamentally different concerns. Separation enables:
- Different sources and destinations (e.g., Bitbucket → local)
- Different implementations (API vs local vs S3)
- Clearer interfaces with focused responsibilities

### Decision 2: All Components Required
**Date:** 2025-11-01
**Rationale:** No optional parameters. Use explicit NoOp implementations (e.g., `NoOpConverter()`) instead of `None`. Makes intent clear and prevents null-check complexity.

### Decision 3: Configuration-Driven Component Selection
**Date:** 2025-11-01
**Rationale:** YAML config specifies which implementation to use. Enables:
- Changing implementations without code changes
- Different configs for different environments
- Easy testing with different component combinations

### Decision 4: Depth-Based Initial Sync
**Date:** 2025-11-01
**Rationale:** When no sync state exists, `depth` controls how much history to process:
- `depth=0`: Do nothing (explicit)
- `depth=1`: Only latest (safe default)
- `depth=N`: Last N versions (controlled backfill)
Prevents accidental full-history processing.

### Decision 5: Sync State in Destination
**Date:** 2025-11-01
**Rationale:** Sync state tracks "what we've uploaded" so it belongs with the uploads. Destination maintains state file showing what's been processed.

---

## 13. Extensibility

### Adding a New Source Implementation

```python
# 1. Create new source class
class S3Source(SourceInterface):
    def __init__(self, config: dict):
        self.bucket = config['bucket']
        self.s3_client = boto3.client('s3', ...)

    def get_changed_files(self, ...):
        # Implementation using S3 API
        pass

    # ... implement all interface methods

# 2. Register in plugin registry
registry.register_source('s3', S3Source)

# 3. Use in config
# source:
#   implementation: s3
#   config:
#     bucket: my-excel-files
#     region: eu-west-1
```

### Adding a New Destination Implementation

Same process as source, implementing `DestinationInterface`

### Adding a New Converter Implementation

```python
class OnlineAPIConverter(ConverterInterface):
    """Use online conversion API"""
    def needs_conversion(self, file_path):
        return file_path.suffix == '.xlsb'

    def can_convert(self, file_path):
        return True  # API available everywhere

    def convert(self, input_path, output_dir):
        # Upload to API, download converted file
        pass
```

---

## 14. Performance Considerations

### Large Repositories
- Use narrow `include_patterns` to reduce files scanned
- Use `exclude_patterns` liberally
- Use `depth=1` for incremental processing

### Large Files
- Increase `timeout` in flattener config
- Consider implementing file size limits
- Monitor memory usage

### API Rate Limits
- Bitbucket: 1000 requests/hour typical limit
- Batch operations where possible
- Use local git clone as fallback for heavy operations

### Parallel Processing (Future)
- Process multiple files concurrently
- Requires thread-safe implementations
- Configuration option: `max_concurrent: 4`

---

## 15. Security Considerations

### Secrets Management
- Never commit secrets to git
- Use `.env` for tokens
- Use environment variable substitution: `${VAR_NAME}`
- Restrict permissions on config files: `chmod 600`

### Token Permissions
- Use minimum required permissions
- Separate tokens for source and destination
- Regularly rotate tokens
- Bitbucket App Passwords > Username/Password

### Network Security
- Use HTTPS for all API calls
- Verify SSL certificates
- Timeout network operations
- Log authentication failures (without exposing credentials)

---

## 16. Future Enhancements

### Planned Features
- [ ] Parallel file processing
- [ ] Dry-run mode (simulate without uploading)
- [ ] Detailed progress reporting
- [ ] Webhook integration for triggering
- [ ] Differ component for comparing flats
- [ ] Web UI for configuration
- [ ] Metrics and monitoring
- [ ] Advanced filtering (file size, date ranges)

### Potential Implementations
- [ ] GitHub Source/Destination
- [ ] GitLab Source/Destination
- [ ] S3 Source/Destination
- [ ] Azure Blob Source/Destination
- [ ] HTTP Source (download from URL)
- [ ] SFTP Source/Destination
- [ ] GitPython Source/Destination (local git)

---

## References

- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Project status and timeline
- [COMPONENT_SPECIFICATIONS.md](COMPONENT_SPECIFICATIONS.md) - Detailed interface specs
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment instructions
- [FLATTENER_SPECS.md](FLATTENER_SPECS.md) - Flattener component details

---

**END OF ARCHITECTURE DOCUMENT V3**
