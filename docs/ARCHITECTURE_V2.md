# Excel Differ - Modular Architecture

**Version:** 2.1
**Date:** 2025-10-29
**Status:** Design Document

---

## 1. Overview

The Excel Differ system is designed as a **modular, composable architecture** where each component functions independently and is coordinated by an orchestrator. This design enables:

- **Independent development and deployment** of each component
- **Clear workflow orchestration** for automated processing
- **Easy testing** of individual components
- **Flexible integration** patterns (CLI, API, library)

---

## 2. Core Components

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                          │
│         (Main workflow coordination component)           │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ Coordinates workflow:
                  │ 1. Check for new files (Git)
                  │ 2. Download if needed (Git)
                  │ 3. Flatten each file (Flattener)
                  │ 4. Upload flats (Git)
                  │
     ┌────────────┼────────────┬──────────────┐
     │            │            │              │
     ▼            ▼            ▼              ▼
┌─────────┐  ┌─────────┐  ┌──────────┐  ┌─────────┐
│   GIT   │  │FLATTENER│  │CONVERTER │  │  DIFFER │
│Component│  │Component│  │Component │  │Component│
└─────────┘  └────┬────┘  └──────────┘  └─────────┘
     │            │
     │            └──────► Uses Converter for XLSB/XLS
     │
     └──────► Download/Upload files and folders
```

---

## 3. Component Specifications

### 3.1 Git Component

**Purpose:** Handle all Git operations for downloading and uploading Excel files and flattened outputs.

**Responsibilities:**
- Check remote repository for new or changed Excel files
- Download Excel files from repository
- Upload flattened directories to repository
- Handle Git authentication (SSH keys, tokens)
- Manage branches (same or different for source/flats)
- Handle concurrent operations and conflicts

**Key Operations:**
- `check_for_new_files(repo_url, branch, file_patterns)` → List of changed files
- `download_files(repo_url, branch, file_paths, local_dir)` → Downloaded file paths
- `upload_directory(local_dir, repo_url, branch, commit_message)` → Commit SHA
- `clone_or_pull(repo_url, branch, local_dir)` → Repository state
- `list_files(repo_url, branch, file_patterns)` → File inventory

**Inputs:**
- Repository URL (SSH or HTTPS)
- Branch name
- Authentication credentials
- File patterns to match (e.g., `*.xlsx`, `*.xlsm`)
- Commit metadata

**Outputs:**
- List of changed/new files
- Downloaded files
- Commit SHA for uploads
- Repository state information

**Dependencies:**
- Python library: GitPython
- System: git binary
- SSH keys or access tokens for authentication

**Interfaces:**
- Python API: `GitComponent.check_for_new_files()`, `GitComponent.download_files()`, etc.
- CLI: `excel-git check-new <repo> --branch main`

**Status:** 🔴 **TO BE SPECIFIED IN DETAIL**

---

### 3.2 Flattener Component

**Purpose:** Transform binary Excel workbooks into deterministic text representations.

**Responsibilities:**
- Load and parse Excel files (.xlsx, .xlsm, .xlsb, .xls)
- Extract all content (formulas, values, formatting, VBA, etc.)
- Generate structured text files and manifest
- Handle conversion requirements for binary formats

**Inputs:**
- Excel file path (any supported format)
- Configuration options (include_computed, etc.)
- Optional origin metadata (repo, commit, path)

**Outputs:**
- Flat directory with structured text files
- Manifest JSON with metadata and file inventory
- Warnings/errors list

**Dependencies:**
- Converter Component (for XLSB/XLS files)
- Python libraries: openpyxl, lxml, oletools

**Interfaces:**
- Python API: `Flattener.flatten(input_file, **options)`
- CLI: `excel-flattener flatten <file> --output <dir>`

**Status:** ✅ **FULLY SPECIFIED** - See [FLATTENER_SPECS.md](FLATTENER_SPECS.md)

---

### 3.3 Converter Component

**Purpose:** Convert legacy Excel formats to modern OOXML format.

**Responsibilities:**
- Convert .xlsb → .xlsm
- Convert .xls → .xlsx
- Validate conversion success
- Handle conversion timeouts and errors
- Optional file caching

**Inputs:**
- Excel file path (.xlsb or .xls)
- Conversion configuration (tool path, timeout)

**Outputs:**
- Converted file path (.xlsm or .xlsx)
- Conversion status and errors

**Dependencies:**
- External tool (e.g., LibreOffice headless mode)
- System: subprocess, temp directory

**Interfaces:**
- Python API: `Converter.convert(input_file, output_dir)`
- CLI: `excel-converter convert <file> --output <dir>`

**Implementation Details:** To be defined by this component (not specified here)

**Status:** 🔴 **TO BE SPECIFIED IN DETAIL**

---

### 3.4 Differ Component

**Purpose:** Compare two flattened outputs and generate structured diff.

**Responsibilities:**
- Load two flat directories and their manifests
- Compare files and detect changes (added, removed, modified)
- Generate structured JSON diff (typed changes)
- Generate unified text diff (git-style patch)
- Provide diff statistics and summary

**Inputs:**
- Two flat directory paths
- Comparison options (context lines, output format)

**Outputs:**
- JSON diff (array of typed change objects)
- Unified diff text (patch format)
- Summary statistics (counts of changes by type)

**Dependencies:**
- Python libraries: difflib, json
- Flattener manifests for file inventory

**Interfaces:**
- Python API: `Differ.compare(flat_a, flat_b, **options)`
- CLI: `excel-differ compare <flat_a> <flat_b>`

**Status:** 🔴 **TO BE SPECIFIED IN DETAIL**

---

### 3.5 Orchestrator Component

**Purpose:** Coordinate the complete workflow: check for new files, download, flatten, upload.

**Responsibilities:**
- Manage overall workflow execution
- Call Git component to check for new Excel files
- Download new/changed files
- Call Flattener for each Excel file
- Collect all flattened outputs
- Upload flats to repository (same or different repo/branch)
- Handle errors and retries
- Provide progress reporting

**Workflow:**
```
1. Orchestrator calls Git.check_for_new_files(source_repo, source_branch, patterns)
   → Returns: List of new/changed Excel files

2. If no new files:
   → Done (exit)

3. If new files found:
   → Orchestrator calls Git.download_files(source_repo, source_branch, file_list, temp_dir)
   → Returns: Local paths to downloaded Excel files

4. For each downloaded Excel file:
   → Orchestrator calls Flattener.flatten(file_path, output_dir)
   → Returns: Flat directory path, manifest, warnings

5. After all files flattened:
   → Orchestrator calls Git.upload_directory(flats_dir, target_repo, target_branch, message)
   → Returns: Commit SHA

6. Done
```

**Configuration:**
- Source repository (where Excel files live)
- Source branch
- Target repository (where flats go, can be same as source)
- Target branch (can be same or different from source)
- File patterns to monitor (e.g., `**/*.xlsx`, `**/*.xlsm`)
- Flattener options (include_computed, etc.)

**Inputs:**
- Configuration file or environment variables
- Optional: Specific files to process (bypass change detection)

**Outputs:**
- Processing summary (files processed, warnings, commit SHA)
- Logs of all operations
- Exit status (success/failure)

**Error Handling:**
- Continue processing other files if one fails
- Collect all errors and warnings
- Report summary at end
- Non-zero exit code if any errors

**Interfaces:**
- Python API: `Orchestrator.run(config)`
- CLI: `excel-orchestrator run --config config.yaml`
- CLI: `excel-orchestrator run --source-repo <url> --target-repo <url>`

**Status:** 🔴 **TO BE SPECIFIED IN DETAIL**

---

## 4. Component Interaction Workflow

### 4.1 Automated Workflow (Orchestrator-Driven)

```
┌──────────────┐
│ Orchestrator │
└──────┬───────┘
       │
       ├─→ 1. Check for new Excel files
       │   Git.check_for_new_files(repo, branch, "**/*.xlsx")
       │   → ["finance/budget.xlsx", "sales/report.xlsm"]
       │
       ├─→ 2. Download new files (if any)
       │   Git.download_files(repo, branch, file_list, "./temp")
       │   → ["./temp/budget.xlsx", "./temp/report.xlsm"]
       │
       ├─→ 3. Flatten each file
       │   Flattener.flatten("./temp/budget.xlsx", "./flats")
       │   → {"flat_dir": "./flats/budget-flat-...", "warnings": []}
       │
       │   Flattener.flatten("./temp/report.xlsm", "./flats")
       │   → {"flat_dir": "./flats/report-flat-...", "warnings": []}
       │
       └─→ 4. Upload all flats
           Git.upload_directory("./flats", target_repo, branch, "Add flats for 2 files")
           → "commit_sha: abc123..."
```

**Key Points:**
- Orchestrator coordinates entire workflow
- Each component is called in sequence
- Errors at any stage are collected and reported
- Workflow can run unattended (CI/CD, cron job)

---

### 4.2 Manual Workflow (Direct Component Usage)

**Flatten a single file:**
```python
from excel_flattener import Flattener

flattener = Flattener()
result = flattener.flatten("budget.xlsx", output_dir="./flats")
print(f"Flat created: {result['flat_dir']}")
```

**Compare two files:**
```python
from excel_flattener import Flattener
from excel_differ import Differ

flattener = Flattener()
flat_a = flattener.flatten("old.xlsx", "./temp/a")
flat_b = flattener.flatten("new.xlsx", "./temp/b")

differ = Differ()
diff = differ.compare(flat_a['flat_dir'], flat_b['flat_dir'])
print(f"Formulas changed: {diff['summary']['formulas_changed']}")
```

**Git operations:**
```python
from excel_git import GitComponent

git = GitComponent(auth_token="...")
new_files = git.check_for_new_files(
    repo_url="git@github.com:org/repo.git",
    branch="main",
    patterns=["**/*.xlsx"]
)
print(f"New files: {new_files}")
```

---

### 4.3 Orchestrator Configuration Example

**File: `config.yaml`**
```yaml
# Source repository (where Excel files are)
source:
  repo_url: git@github.com:company/excel-files.git
  branch: main
  patterns:
    - "**/*.xlsx"
    - "**/*.xlsm"
    - "**/*.xlsb"
  auth:
    type: ssh_key
    key_path: ~/.ssh/id_rsa

# Target repository (where flats go)
target:
  repo_url: git@github.com:company/excel-flats.git  # Can be same as source
  branch: flats                                      # Can be different branch
  auth:
    type: ssh_key
    key_path: ~/.ssh/id_rsa

# Flattener options
flattener:
  include_computed: false
  extraction_timeout: 900

# Orchestrator options
orchestrator:
  continue_on_error: true   # Keep processing other files if one fails
  temp_dir: /tmp/excel-orchestrator
  max_concurrent: 1         # Process files one at a time (for now)
```

**Usage:**
```bash
# Run orchestrator with config file
excel-orchestrator run --config config.yaml

# Or via environment variables
EXCEL_SOURCE_REPO="git@github.com:company/excel-files.git" \
EXCEL_SOURCE_BRANCH="main" \
EXCEL_TARGET_REPO="git@github.com:company/excel-flats.git" \
EXCEL_TARGET_BRANCH="flats" \
excel-orchestrator run

# Or as one-off command
excel-orchestrator run \
  --source-repo git@github.com:company/excel-files.git \
  --source-branch main \
  --target-repo git@github.com:company/excel-flats.git \
  --target-branch flats \
  --patterns "**/*.xlsx"
```

---

## 5. Directory Structure (Proposed)

```
excel-differ/
├── components/
│   ├── flattener/              # Flattener component (PRIMARY FOCUS)
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── flattener.py
│   │   │   ├── normalizer.py
│   │   │   ├── metadata.py
│   │   │   ├── sheets.py
│   │   │   ├── vba.py
│   │   │   └── manifest.py
│   │   ├── tests/
│   │   ├── docs/
│   │   │   └── FLATTENER_SPECS.md
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   ├── converter/              # Converter component (FUTURE)
│   │   ├── src/
│   │   ├── tests/
│   │   ├── docs/
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   ├── differ/                 # Differ component (FUTURE)
│   │   ├── src/
│   │   ├── tests/
│   │   ├── docs/
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   ├── git/                    # Git component (FUTURE)
│   │   ├── src/
│   │   ├── tests/
│   │   ├── docs/
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   └── orchestrator/           # Orchestrator component (FUTURE)
│       ├── src/
│       ├── tests/
│       ├── docs/
│       ├── pyproject.toml
│       └── README.md
│
├── shared/
│   └── common/                 # Shared utilities
│       ├── src/
│       │   ├── config.py
│       │   ├── storage.py
│       │   └── logging.py
│       └── pyproject.toml
│
├── docs/                       # System-wide documentation
│   ├── ARCHITECTURE_V2.md      # This file
│   └── FLATTENER_SPECS.md      # Flattener specs
│
└── README.md                   # Project overview
```

---

## 6. Deployment Models

### 6.1 Standalone Library (Current Focus)

**Use Case:** Import flattener as Python library in your code.

```python
from excel_flattener import Flattener

flattener = Flattener()
result = flattener.flatten("budget.xlsx", output_dir="./flats")
```

**Deployment:**
- Install: `pip install excel-flattener`
- Dependencies: Python 3.9+, openpyxl, lxml, oletools

---

### 6.2 Command-Line Tool

**Use Case:** Run components from terminal/scripts.

```bash
# Flatten a file
excel-flattener flatten budget.xlsx --output ./flats

# Check for new files in repo
excel-git check-new git@github.com:org/repo.git --branch main

# Run orchestrator
excel-orchestrator run --config config.yaml
```

**Deployment:**
- Install: `pip install excel-differ[cli]`
- Use in CI/CD scripts, git hooks, automation

---

### 6.3 CI/CD Integration (Future)

**GitHub Actions Workflow:**

```yaml
name: Excel Flattening Workflow
on:
  push:
    branches: [main]
    paths:
      - '**.xlsx'
      - '**.xlsm'

jobs:
  flatten:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Excel Differ
        run: pip install excel-differ

      - name: Run Orchestrator
        env:
          SOURCE_REPO: ${{ github.repository }}
          TARGET_REPO: ${{ github.repository }}
          TARGET_BRANCH: flats
        run: |
          excel-orchestrator run \
            --source-repo $SOURCE_REPO \
            --source-branch main \
            --target-repo $TARGET_REPO \
            --target-branch flats

      - name: Report Results
        run: echo "Processing complete"
```

---

## 7. Configuration Management

### 7.1 Configuration Hierarchy

```
1. Defaults (in code)
   ↓
2. System config file (/etc/excel-differ/config.yaml)
   ↓
3. User config file (~/.excel-differ/config.yaml)
   ↓
4. Project config file (./excel-differ.yaml)
   ↓
5. Environment variables (EXCEL_*)
   ↓
6. Command-line arguments
```

**Later settings override earlier settings.**

---

### 7.2 Configuration Format

**File: excel-differ.yaml**

```yaml
# Flattener settings
flattener:
  include_computed: false
  extraction_timeout: 900
  enable_vba: true
  enable_charts: true
  enable_tables: true

# Converter settings (future)
converter:
  tool: libreoffice
  timeout: 300

# Git settings
git:
  source:
    repo_url: git@github.com:company/excel-files.git
    branch: main
    patterns: ["**/*.xlsx", "**/*.xlsm"]
  target:
    repo_url: git@github.com:company/excel-flats.git
    branch: flats
  auth:
    type: ssh_key
    key_path: ~/.ssh/id_rsa

# Orchestrator settings
orchestrator:
  continue_on_error: true
  temp_dir: /tmp/excel-orchestrator
  max_concurrent: 1

# Storage settings
storage:
  temp_dir: /tmp/excel-differ
  output_dir: ./flats
  max_file_size: 209715200  # 200 MB

# Logging
logging:
  level: INFO
  file: excel-differ.log
  format: json
```

---

## 8. Error Handling Strategy

### 8.1 Error Categories

**Input Errors:**
- File not found
- Invalid file format
- File too large
- Password-protected workbook

**Response:** Clear error message, exit code 1, suggest fix.

**Configuration Errors:**
- Missing dependencies
- Invalid config file
- Insufficient permissions
- Git authentication failure

**Response:** Error message with setup instructions, exit code 2.

**Processing Errors:**
- Corrupt Excel file
- Timeout during extraction
- Out of memory
- Git operation failure

**Response:** Error message, partial results if possible, exit code 3.

**System Errors:**
- Disk full
- Network timeout
- External tool crash

**Response:** Error message, suggest retry, exit code 4.

---

### 8.2 Orchestrator Error Handling

**Philosophy:** Fail gracefully, continue processing when possible.

```python
# Orchestrator pseudo-code
def run_workflow(config):
    errors = []
    successes = []

    try:
        # Step 1: Check for new files
        new_files = git.check_for_new_files(...)
        if not new_files:
            logger.info("No new files to process")
            return {"status": "success", "processed": 0}

        # Step 2: Download files
        downloaded = git.download_files(new_files, ...)

        # Step 3: Flatten each file
        for file in downloaded:
            try:
                result = flattener.flatten(file, ...)
                successes.append(result)
            except Exception as e:
                errors.append({"file": file, "error": str(e)})
                if not config.continue_on_error:
                    raise

        # Step 4: Upload flats
        if successes:
            commit_sha = git.upload_directory(flats_dir, ...)
            logger.info(f"Uploaded flats: {commit_sha}")

        # Report results
        return {
            "status": "success" if not errors else "partial",
            "processed": len(successes),
            "errors": errors
        }

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        return {"status": "failed", "error": str(e)}
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Per Component:**
- Flattener: Test each extraction module independently
- Converter: Test format conversion
- Differ: Test diff algorithms
- Git: Test git operations (mocked)
- Orchestrator: Test workflow logic (mocked components)

**Coverage Target:** 80%+

---

### 9.2 Integration Tests

**Cross-Component:**
- Flattener + Converter: Test XLSB extraction
- Flattener + Differ: Full compare workflow
- Git + Orchestrator: Test repository operations
- Full workflow: End-to-end orchestration

---

### 9.3 System Tests

**Complete Workflow:**
- Set up test repositories
- Add Excel files
- Run orchestrator
- Verify flats uploaded correctly
- Check git history

---

## 10. Implementation Priorities

### 10.1 Phase 1: Standalone Flattener (CURRENT)

**Goal:** Production-ready, standalone flattener component.

**Scope:**
- Core extraction (metadata, sheets, formulas, values, formats)
- VBA extraction
- Minimal normalisation
- Manifest generation
- CLI interface
- Comprehensive tests
- Complete documentation

**Timeline:** 2-4 weeks

**Success Criteria:**
- Can flatten .xlsx and .xlsm files reliably
- Output is deterministic
- Diffs are clean
- Handles errors gracefully
- Well-tested (80%+ coverage)
- Documented

---

### 10.2 Phase 2: Converter Component

**Goal:** Separate XLSB/XLS conversion logic.

**Scope:**
- Extract conversion from flattener
- Support multiple conversion tools (LibreOffice, etc.)
- Handle timeouts and errors
- Caching (optional)

**Timeline:** 1 week

---

### 10.3 Phase 3: Git Component

**Goal:** Git operations for download/upload.

**Scope:**
- Check for new files
- Download files from repository
- Upload flats to repository
- Handle authentication
- Branch management
- Conflict resolution

**Timeline:** 1-2 weeks

---

### 10.4 Phase 4: Orchestrator

**Goal:** Workflow coordination.

**Scope:**
- Workflow engine
- Configuration management
- Error handling and retries
- Progress reporting
- CLI interface

**Timeline:** 1-2 weeks

---

### 10.5 Phase 5: Differ Component

**Goal:** Compare flattened outputs.

**Scope:**
- Load and compare flats
- Generate structured diff
- Summary statistics

**Timeline:** 1 week

---

## 11. Decision Log

### Decision 1: Orchestrator-Based Architecture

**Date:** 2025-10-29

**Context:** User wants a main component that coordinates Git operations and flattening.

**Decision:** Adopt orchestrator pattern with Git, Flattener, and Converter as independent components.

**Rationale:**
- Clear workflow coordination
- Components remain independent and testable
- Easy to extend workflow with new steps
- Follows "orchestration over choreography" pattern

---

### Decision 2: Git Component for Download/Upload

**Date:** 2025-10-29

**Context:** Need to check for new files, download them, and upload flats.

**Decision:** Create dedicated Git component responsible for all repository operations.

**Rationale:**
- Separates git concerns from flattening
- Can be reused across workflows
- Easier to test git logic independently
- Handles authentication in one place

---

### Decision 3: Minimal Normalisation

**Date:** 2025-10-29

**Context:** User wants to see all changes reflected in diffs, including case and formatting.

**Decision:** Extract data as-is from Excel, only normalise for consistency (encoding, line endings, sorting).

**Rationale:**
- All changes visible in diffs
- No hidden modifications
- More transparent
- Easier to debug

---

### Decision 4: British English in Documentation

**Date:** 2025-10-29

**Context:** User preference for British English.

**Decision:** Use British English throughout documentation and user-facing text.

**Rationale:**
- User preference
- Code attributes may use American English (following conventions)
- Documentation should match user's language

---

## 12. Open Questions

### For User to Decide:

1. **Git Repository Organisation:**
   - Use same repo for source and flats, just different branches?
   - Or completely separate repositories?
   - How to organise flats directory structure?

2. **File Patterns:**
   - What patterns to match for Excel files? (e.g., `**/*.xlsx`, `finance/**/*.xlsm`)
   - Exclude any patterns? (e.g., temp files, ~$*.xlsx)

3. **Processing Behaviour:**
   - Should orchestrator process all changed files or only new files?
   - How to handle deleted files (should we delete flats too)?
   - Continue processing if one file fails, or stop immediately?

4. **Scheduling:**
   - Run orchestrator manually, on git hook, via cron, or CI/CD?
   - How often to check for new files?

5. **Converter Implementation:**
   - Stick with LibreOffice or explore alternatives?
   - Is XLSB support critical?

---

## 13. Next Steps

1. **Complete Flattener Implementation** (Phase 1)
   - Implement core extraction
   - Write comprehensive tests
   - Document CLI usage

2. **Define Git Component Specs** (Phase 3)
   - Detailed specification document
   - API design
   - Authentication strategy

3. **Define Orchestrator Specs** (Phase 4)
   - Workflow definition
   - Configuration format
   - Error handling rules

4. **User Review and Feedback**
   - Answer open questions
   - Clarify requirements
   - Adjust priorities

---

## Appendix A: Glossary

- **Flattener:** Component that converts Excel to text
- **Flat:** Flattened representation of workbook at a point in time
- **Manifest:** JSON file listing all extracted files and metadata
- **Normalisation:** Process of making output deterministic (minimal)
- **Computed Values:** Displayed cell values (formula results)
- **Literal Values:** Non-formula cell values
- **Origin:** Source repository and commit information
- **Converter:** Tool to convert legacy Excel formats
- **Orchestrator:** Main coordination component for workflow
- **Git Component:** Handles repository download/upload operations

---

## Appendix B: References

- [FLATTENER_SPECS.md](FLATTENER_SPECS.md) - Complete flattener specifications
- [Differ Requirements.md](Differ%20Requirements.md) - Original system requirements (historical)

---

**END OF ARCHITECTURE DOCUMENT**
