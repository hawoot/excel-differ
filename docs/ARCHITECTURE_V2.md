# Excel Differ - Modular Architecture

**Version:** 2.0
**Date:** 2025-10-29
**Status:** Design Document

---

## 1. Overview

The Excel Differ system is designed as a **modular, composable architecture** where each component can function independently or be combined into larger systems. This design enables:

- **Independent development and deployment** of each component
- **Flexible integration** patterns (CLI, API, library)
- **Easy testing** of individual components
- **Clear separation of concerns**

---

## 2. Core Components

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    EXCEL DIFFER SYSTEM                       │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐     ┌──────────────┐
│  FLATTENER   │      │   CONVERTER  │     │ GIT HANDLER  │
│  Component   │◄────►│   Component  │     │  Component   │
└──────────────┘      └──────────────┘     └──────────────┘
        │                                            │
        └─────────────────┬──────────────────────────┘
                          ▼
                  ┌──────────────┐
                  │    DIFFER    │
                  │  Component   │
                  └──────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  CLI Layer   │  │  API Layer   │  │ Library API  │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 3. Component Specifications

### 3.1 Flattener Component

**Purpose:** Transform binary Excel workbooks into deterministic text representations.

**Responsibilities:**
- Load and parse Excel files (.xlsx, .xlsm, .xlsb, .xls)
- Extract all content (formulas, values, formatting, VBA, etc.)
- Normalize data for deterministic output
- Generate structured text files and manifest
- Handle conversion of legacy formats

**Inputs:**
- Excel file path (any supported format)
- Configuration options (include_evaluated, etc.)
- Optional origin metadata (repo, commit, path)

**Outputs:**
- Snapshot directory with structured text files
- Manifest JSON with metadata and file inventory
- Warnings/errors list

**Dependencies:**
- Converter Component (for XLSB/XLS files)
- Python libraries: openpyxl, lxml, oletools

**Interfaces:**
- Python API: `Flattener.flatten(input_file, **options)`
- CLI: `excel-flattener flatten <file> --output <dir>`

**Status:** ✅ **PRIMARY FOCUS FOR CURRENT IMPLEMENTATION**

**Specification:** See [FLATTENER_SPECS.md](FLATTENER_SPECS.md)

---

### 3.2 Converter Component

**Purpose:** Convert legacy Excel formats to modern OOXML format.

**Responsibilities:**
- Convert .xlsb → .xlsm using LibreOffice
- Convert .xls → .xlsx using LibreOffice
- Validate conversion success
- Handle conversion timeouts and errors
- Cache converted files (optional)

**Inputs:**
- Excel file path (.xlsb or .xls)
- Converter path (LibreOffice binary)
- Timeout configuration

**Outputs:**
- Converted file path (.xlsm or .xlsx)
- Conversion status and errors

**Dependencies:**
- External: LibreOffice (headless mode)
- System: subprocess, temp directory

**Interfaces:**
- Python API: `Converter.convert(input_file, output_dir)`
- CLI: `excel-converter convert <file> --output <dir>`

**Current Implementation:** Embedded in flattener (`converter.py`)

**Future:** Extract to standalone component

**Status:** ⚠️ **SPECIFIED BUT NOT YET SEPARATED**

**Key Design Questions:**
- Should conversion be synchronous or async?
- Should we cache converted files? Where? For how long?
- Should we support other conversion tools (e.g., python-xlsb)?
- How do we handle platform differences (Linux/Windows/macOS)?

---

### 3.3 Differ Component

**Purpose:** Compare two flattened snapshots and generate structured diff output.

**Responsibilities:**
- Load two snapshot directories and their manifests
- Compare files and detect changes (added, removed, modified)
- Generate structured JSON diff (typed changes)
- Generate unified text diff (git-style patch)
- Provide diff statistics and summary

**Inputs:**
- Two snapshot directory paths
- Comparison options (context lines, output format)

**Outputs:**
- JSON diff (array of typed change objects)
- Unified diff text (patch format)
- Summary statistics (counts of changes by type)

**Dependencies:**
- Python libraries: difflib, json
- Flattener manifests for file inventory

**Interfaces:**
- Python API: `Differ.compare(snapshot_a, snapshot_b, **options)`
- CLI: `excel-differ compare <snapshot_a> <snapshot_b>`

**Status:** 🔴 **NOT YET SPECIFIED OR IMPLEMENTED**

**Key Design Questions:**
- Should differ work on snapshots only, or also accept raw Excel files?
- How to handle moved/renamed sheets?
- How to handle large diffs (100K+ cell changes)?
- Should we provide visual diff output (HTML/web)?

---

### 3.4 Git Handler Component

**Purpose:** Integrate flattened snapshots with Git repositories.

**Responsibilities:**
- Clone and manage snapshot repository
- Commit flattened snapshots with metadata
- Create and manage branches
- Handle concurrent commits with retry logic
- Query snapshot history

**Inputs:**
- Snapshot directory
- Repository URL and credentials
- Commit metadata (message, author, origin)

**Outputs:**
- Commit SHA
- Updated repository state
- Errors and warnings

**Dependencies:**
- Python library: GitPython
- System: git binary

**Interfaces:**
- Python API: `GitHandler.commit_snapshot(snapshot_dir, repo_url, **metadata)`
- CLI: `excel-git commit <snapshot_dir> --repo <url>`

**Status:** 🔴 **NOT YET SPECIFIED**

**Key Design Questions:**
- Where to store snapshot repos (local cache vs remote-only)?
- How to organize snapshots in git (directory structure)?
- How to handle large binary files (Git LFS)?
- Should we support GitHub/GitLab API integration (PRs, issues)?

---

### 3.5 API Server Component

**Purpose:** Provide HTTP REST API for all components.

**Responsibilities:**
- Accept file uploads and job submissions
- Queue and execute async jobs (flatten, compare, commit)
- Return job status and results
- Stream large results (archives, diffs)
- Handle authentication and rate limiting

**Inputs:**
- HTTP requests (POST /flatten, POST /compare, GET /jobs/{id})
- Configuration (ports, storage paths, timeouts)

**Outputs:**
- HTTP responses (JSON, file streams)
- Job status updates
- Stored results (temp files, archives)

**Dependencies:**
- Web framework: FastAPI
- Job queue: Celery or multiprocessing
- Storage: filesystem or S3

**Interfaces:**
- REST API endpoints (see original requirements doc)
- Webhooks/callbacks for job completion

**Status:** 🔴 **NOT YET SPECIFIED FOR V2**

**Key Design Questions:**
- Authentication strategy (API keys, OAuth, mTLS)?
- Job queue implementation (Celery, RQ, or custom)?
- Storage strategy (local filesystem, S3, database)?
- Deployment model (Docker, k8s, serverless)?

---

## 4. Component Interaction Patterns

### 4.1 Flatten Workflow

```
User
  │
  ├─→ Flattener.flatten(file.xlsb)
  │     │
  │     ├─→ Converter.convert(file.xlsb) → file.xlsm
  │     │
  │     ├─→ Extract workbook metadata
  │     ├─→ Extract sheets
  │     ├─→ Extract VBA
  │     ├─→ Generate manifest
  │     │
  │     └─→ Return: snapshot_dir
  │
  └─→ Receive: snapshot_dir, manifest, warnings
```

**Key Points:**
- Flattener depends on Converter (composition)
- Converter is optional (only needed for XLSB/XLS)
- All extraction happens synchronously in-process

---

### 4.2 Compare Workflow

```
User
  │
  ├─→ Differ.compare(file_a.xlsx, file_b.xlsx)
  │     │
  │     ├─→ Flattener.flatten(file_a.xlsx) → snapshot_a
  │     │
  │     ├─→ Flattener.flatten(file_b.xlsx) → snapshot_b
  │     │
  │     ├─→ Load manifests
  │     ├─→ Compare files (formula, values, formats, etc.)
  │     ├─→ Generate JSON diff
  │     ├─→ Generate unified diff
  │     │
  │     └─→ Return: diff_json, diff_unified, summary
  │
  └─→ Receive: structured diff
```

**Key Points:**
- Differ depends on Flattener (composition)
- Differs works on snapshot directories (not raw Excel)
- Can also accept pre-flattened snapshots (skip flatten step)

---

### 4.3 Git Commit Workflow

```
User/CI Hook
  │
  ├─→ GitHandler.commit_snapshot(file.xlsx, repo_url, metadata)
  │     │
  │     ├─→ Flattener.flatten(file.xlsx) → snapshot_dir
  │     │
  │     ├─→ Clone/pull repo (if not cached)
  │     │
  │     ├─→ Copy snapshot to repo path
  │     │
  │     ├─→ git add, commit, push
  │     │     ├─→ Retry on conflict
  │     │     └─→ Handle errors
  │     │
  │     └─→ Return: commit_sha, repo_path
  │
  └─→ Receive: commit info
```

**Key Points:**
- Git Handler depends on Flattener
- Handles repository state management
- Provides atomic commit operations
- Handles concurrency and conflicts

---

### 4.4 API Server Workflow

```
Client (curl/browser)
  │
  ├─→ POST /api/v1/flatten (upload file)
  │     │
  │     ├─→ Validate request
  │     ├─→ Create job
  │     ├─→ Return: 202 Accepted, job_id
  │     │
  │     └─→ [Background Worker]
  │           │
  │           ├─→ Flattener.flatten(file) → snapshot
  │           ├─→ Archive snapshot → zip
  │           ├─→ Store result
  │           └─→ Mark job complete
  │
  ├─→ GET /api/v1/jobs/{job_id}
  │     │
  │     └─→ Return: job status, result (if complete)
  │
  └─→ GET /api/v1/results/{job_id}/download
        │
        └─→ Stream: snapshot.zip
```

**Key Points:**
- API Server orchestrates all components
- Uses async job queue for long-running tasks
- Provides HTTP interface to all functionality
- Handles state management and cleanup

---

## 5. Data Flow

### 5.1 File Processing Pipeline

```
┌──────────────┐
│ Excel File   │
│ (.xlsb/.xlsx)│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Converter   │ (if needed)
│ .xlsb→.xlsm  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Flattener   │
│  Extract &   │
│  Normalize   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Snapshot    │
│  Directory   │
│  + Manifest  │
└──────┬───────┘
       │
       ├─────────────┬──────────────┐
       │             │              │
       ▼             ▼              ▼
  ┌─────────┐  ┌─────────┐  ┌─────────┐
  │ Git     │  │ Differ  │  │ Archive │
  │ Commit  │  │ Compare │  │ (ZIP)   │
  └─────────┘  └─────────┘  └─────────┘
```

---

## 6. Storage Architecture

### 6.1 Directory Structure (Proposed)

```
excel-differ/
├── components/
│   ├── flattener/              # Flattener component (CURRENT FOCUS)
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
│   └── git-handler/            # Git Handler component (FUTURE)
│       ├── src/
│       ├── tests/
│       ├── docs/
│       ├── pyproject.toml
│       └── README.md
│
├── applications/
│   ├── cli/                    # Command-line application
│   │   ├── src/
│   │   │   └── main.py
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   └── api-server/             # API server application (FUTURE)
│       ├── src/
│       ├── docker/
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
│   └── FLATTENER_SPECS.md      # Component specs
│
└── README.md                   # Project overview
```

---

## 7. Open Questions for User

### 7.1 Platform & Environment

**Questions:**
1. **What platform(s) will you primarily use?**
   - Windows with Excel installed?
   - Linux server without Excel?
   - Both?

2. **Is LibreOffice available?**
   - Can you install it?
   - Do you have admin rights?
   - If not, can you avoid XLSB files?

3. **What errors did you encounter with named ranges?**
   - Can you provide specific examples?
   - Were they extraction errors or diff errors?
   - What types of named ranges caused issues?

### 7.2 Use Cases & Requirements

**Questions:**
4. **What's your primary use case?**
   - Just flatten Excel files to text?
   - Compare versions and see diffs?
   - Track changes in git?
   - All of the above?

5. **Do you need evaluated values?**
   - Or are formulas and hardcoded values enough?
   - Are cached values acceptable (not recomputed)?

6. **What Excel features do you actually use?**
   - VBA macros?
   - Charts and pivots?
   - Tables?
   - Data connections?
   - Complex formatting?

### 7.3 Deployment & Integration

**Questions:**
7. **How will you use the flattener?**
   - As a Python library in your code?
   - As a command-line tool?
   - Via an API server?

8. **Do you want git integration?**
   - Automatic commits to a snapshot repo?
   - Manual workflow (you handle git)?

9. **Do you need the differ component?**
   - Or can you use git diff on the flattened files?
   - Need structured JSON output?

---

## 8. Implementation Priorities

### 8.1 Phase 1: Standalone Flattener (CURRENT)

**Goal:** Production-ready, standalone flattener component.

**Scope:**
- Core extraction (metadata, sheets, formulas, values, formats)
- VBA extraction (with password protection handling)
- Normalization for deterministic output
- Manifest generation
- CLI interface
- Comprehensive tests
- Complete documentation

**Out of Scope (for now):**
- Tables, charts, pivots (placeholders only)
- Styles and themes (placeholders only)
- Calculation chain, external links, connections (placeholders only)
- API server
- Git integration
- Differ component

**Timeline:** 2-4 weeks

**Success Criteria:**
- Can flatten .xlsx and .xlsm files reliably
- Output is deterministic (same input → same output)
- Diffs are clean (small changes → small diffs)
- Handles errors gracefully
- Well-tested (80%+ coverage)
- Documented (specs, API docs, CLI help)

---

### 8.2 Future Phases (After User Feedback)

**Phase 2:** Converter Component
- Separate XLSB/XLS conversion logic
- Explore alternatives to LibreOffice

**Phase 3:** Differ Component
- Compare flattened snapshots
- Generate structured diff output

**Phase 4:** Git Handler Component
- Integrate with git repositories
- Handle automatic commits

**Phase 5:** API Server
- HTTP REST API
- Job queue for async processing

---

## 9. Decision Log

### Decision 1: Modular Architecture

**Date:** 2025-10-29

**Context:** User wants to package flattener, converter, git handler separately.

**Decision:** Adopt modular architecture with independent components.

**Rationale:**
- Easier to develop and test
- Users can choose which components to use
- Clear separation of concerns
- Enables flexible deployment models

---

### Decision 2: Flattener as Primary Focus

**Date:** 2025-10-29

**Context:** User encountered issues with current implementation and wants to start fresh.

**Decision:** Focus entirely on flattener component first, defer other components.

**Rationale:**
- Flattener is the foundation for all other components
- User needs reliable flattening now
- Other components depend on stable flattener
- Allows thorough testing and refinement

---

### Decision 3: Specifications Before Implementation

**Date:** 2025-10-29

**Context:** Previous implementation had unclear requirements.

**Decision:** Write exhaustive specifications before coding.

**Rationale:**
- Prevents scope creep
- Ensures completeness
- Enables parallel work (specs → tests → implementation)
- Documents decisions for future maintainers

---

### Decision 4: Archive Current Implementation

**Date:** 2025-10-29

**Context:** User wants to start fresh but not lose existing work.

**Decision:** Archive current code in a branch, reference during rewrite.

**Rationale:**
- Current code has working normalization logic
- VBA extraction works
- Can cherry-pick good parts
- Preserves git history

---

## 10. Next Steps

1. **Review these specifications with user**
   - Answer open questions
   - Clarify requirements
   - Prioritize features

2. **Create folder structure**
   - Set up `components/flattener/` directory
   - Initialize Python package structure
   - Set up testing framework

3. **Begin implementation**
   - Start with core flattener
   - Write tests alongside code
   - Iterate based on feedback

4. **Archive old code**
   - Create `archive/v1` branch
   - Clean up main branch
   - Keep only new implementation

---

**END OF ARCHITECTURE DOCUMENT**
