# Code Walkthrough - Understanding the Excel Diff Server

This guide explains how the Excel Diff Server works, from HTTP request to final result.

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Request Flow](#request-flow)
3. [Key Components](#key-components)
4. [Code Examples](#code-examples)
5. [Where to Start Reading](#where-to-start-reading)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER/CLIENT                              │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP POST /api/v1/flatten
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   FASTAPI SERVER                             │
│  • Validates request                                         │
│  • Saves uploaded file                                       │
│  • Submits job to queue → Returns job_id immediately         │
└────────────────────┬────────────────────────────────────────┘
                     │ Job queued
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              JOB QUEUE (Celery/Redis)                        │
│  • Stores job metadata                                       │
│  • Distributes to available worker                           │
└────────────────────┬────────────────────────────────────────┘
                     │ Worker picks up job
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 CELERY WORKER                                │
│  1. Calls flatten_task()                                     │
│  2. Invokes Flattener Engine                                 │
└────────────────────┬────────────────────────────────────────┘
                     │ Flattener runs
                     ▼
┌─────────────────────────────────────────────────────────────┐
│               FLATTENER ENGINE                               │
│  1. Convert XLSB → XLSM (if needed)                         │
│  2. Load workbook with openpyxl                              │
│  3. Extract metadata, sheets, formulas, values               │
│  4. Normalize everything (uppercase formulas, etc.)          │
│  5. Write to text files in deterministic order               │
│  6. Generate manifest.json                                   │
└────────────────────┬────────────────────────────────────────┘
                     │ Snapshot created
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              RESULT STORAGE                                  │
│  • Job marked as "success"                                   │
│  • Result stored with TTL                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│           USER POLLS /api/v1/jobs/{job_id}                   │
│  • Gets result with snapshot path or archive URL             │
└─────────────────────────────────────────────────────────────┘
```

---

## Request Flow

### Example: Flattening an Excel File

Let's trace what happens when you POST a file to `/api/v1/flatten`:

#### Step 1: API Receives Request

**File**: `src/api/routes/flatten.py`

```python
@router.post("/flatten")
async def flatten_workbook(file: UploadFile, ...):
    # 1. Validate file size
    file_content = await file.read()
    if len(file_content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413)

    # 2. Submit to job queue
    job_id = queue.submit_job(
        job_type=JobType.FLATTEN,
        file=file_content,
        filename=file.filename,
        ...
    )

    # 3. Return immediately with job_id
    return {"status": "accepted", "job_id": job_id}
```

**What happens**: FastAPI validates the request, reads the file into memory, and submits it to the job queue.

#### Step 2: Job Queue Handles It

**File**: `src/core/job_queue.py`

```python
def submit_job(self, job_type, task_func, **kwargs):
    job_id = str(uuid.uuid4())  # Generate unique ID

    # If using Celery:
    celery_task.apply_async(kwargs=kwargs, task_id=job_id)

    # If using multiprocessing:
    executor.submit(task_wrapper, job_id, task_func, **kwargs)

    return job_id
```

**What happens**: The job is queued with a unique ID. Control returns to the API immediately.

#### Step 3: Worker Picks Up Job

**File**: `src/workers/tasks.py`

```python
@celery_app.task(name="flatten_task")
def flatten_task(file, filename, **kwargs):
    # 1. Write file to temp directory
    temp_dir = create_temp_dir()
    input_file = temp_dir / filename
    with open(input_file, "wb") as f:
        f.write(file)

    # 2. Call flattener engine
    flattener = WorkbookFlattener()
    result = flattener.flatten(input_file)

    # 3. Create archive
    archive_path = create_zip_archive(result['snapshot_dir'])

    # 4. Return result
    return {
        "archive_url": "/downloads/...",
        "manifest": result['manifest'].to_dict(),
    }
```

**What happens**: Worker processes the job in the background. User can poll for status.

#### Step 4: Flattener Engine Does the Work

**File**: `src/engine/flattener/workbook.py`

```python
def flatten(self, input_file, ...):
    # 1. Convert XLSB if needed
    working_file = ensure_xlsm_format(input_file)

    # 2. Calculate hash
    file_hash = get_file_hash(input_file)

    # 3. Create snapshot directory
    snapshot_dir = create_snapshot_dir()

    # 4. Load workbook
    wb = load_workbook(working_file, keep_vba=True)

    # 5. Extract everything
    extract_metadata(wb, snapshot_dir)
    extract_sheets(wb, snapshot_dir)
    extract_vba(working_file, snapshot_dir)

    # 6. Generate manifest
    manifest.save(snapshot_dir / "manifest.json")

    return {"snapshot_dir": snapshot_dir, "manifest": manifest}
```

**What happens**: This is where the magic happens - Excel → Text conversion.

---

## Key Components

### 1. Configuration (`src/core/config.py`)

**Purpose**: Central configuration using environment variables.

**Key concept**: All settings come from `.env` file, loaded once at startup.

```python
class Settings(BaseSettings):
    SNAPSHOT_REPO_URL: str
    MAX_UPLOAD_BYTES: int = 200 * 1024 * 1024
    QUEUE_BACKEND: str = "celery"
    # ... etc
```

**Why it matters**: Change behavior without changing code. Just edit `.env`.

### 2. Job Queue (`src/core/job_queue.py`)

**Purpose**: Abstract job submission so we can use Celery OR multiprocessing.

**Key concept**: Abstraction layer with two backends:

```python
class JobQueueBackend(ABC):
    def submit_job(self, job_type, task_func, **kwargs) -> str:
        pass  # Returns job_id

class CeleryBackend(JobQueueBackend):
    # Uses Redis + Celery

class MultiprocessingBackend(JobQueueBackend):
    # Uses ProcessPoolExecutor
```

**Why it matters**: Works with or without Redis. Set `QUEUE_BACKEND` in `.env`.

### 3. Normalizer (`src/engine/flattener/normalizer.py`)

**Purpose**: Make Excel data deterministic and diff-friendly.

**Key functions**:

```python
# Uppercase function names, trim whitespace
normalize_formula("=sum(A1:A10)") → "=SUM(A1:A10)"

# Limit to 15 significant digits
normalize_number(123.456789012345678) → "123.456789012346"

# Consistent date format
normalize_date(datetime(...)) → "2025-10-27T00:00:00Z|45226|yyyy-mm-dd"
```

**Why it matters**: Same input ALWAYS produces same output → perfect for git diffs.

### 4. Workbook Flattener (`src/engine/flattener/workbook.py`)

**Purpose**: Orchestrate the entire flattening process.

**Key method**: `flatten(input_file) → result`

**What it does**:
1. Convert XLSB → XLSM if needed
2. Extract workbook-level metadata
3. Extract each sheet (formulas, values, formats)
4. Extract VBA modules
5. Extract tables, charts, pivots
6. Generate manifest.json

**Why it matters**: This is the core value - turning binary Excel into git-friendly text.

### 5. Sheet Extractor (`src/engine/flattener/sheets.py`)

**Purpose**: Extract all data from a worksheet.

**What it extracts**:
- **Formulas**: Every cell with a formula → `01.Sheet1.formulas.txt`
- **Values**: Every hard-coded value → `01.Sheet1.values_hardcoded.txt`
- **Formats**: Font, fill, alignment → `01.Sheet1.cell_formats.txt`
- **Comments**: Cell comments → `01.Sheet1.comments.txt`

**Format**: Tab-separated, sorted by cell address (row-major order)

```
# ADDRESS   FORMULA
A1         =SUM(A2:A10)
B1         =AVERAGE(B2:B10)
```

**Why it matters**: Deterministic cell order + normalization = perfect for diffs.

### 6. Snapshot Comparison (`src/engine/differ/compare.py`)

**Purpose**: Compare two flattened snapshots.

**How it works**:
1. Load both manifests
2. Compare file hashes (quick check if files changed)
3. For changed files, parse and diff line-by-line
4. Generate structured diff objects

```python
comparison = SnapshotComparison(snapshot_a, snapshot_b)
changes = comparison.get_changed_files()
# → {added: [...], removed: [...], modified: [...]}
```

**Why it matters**: Fast comparison using hashes, detailed diffs only where needed.

### 7. JSON Diff Generator (`src/engine/differ/diff_json.py`)

**Purpose**: Generate typed, structured diff objects.

**Output format**:

```json
[
  {
    "category": "formula",
    "sheet": "Sheet1",
    "cell": "A1",
    "old": "=SUM(A2:A10)",
    "new": "=SUM(A2:A20)"
  },
  {
    "category": "value_hardcoded",
    "sheet": "Sheet1",
    "cell": "B5",
    "old": "100",
    "new": "120"
  }
]
```

**Why it matters**: Machine-readable diffs for automation, UIs, reports.

### 8. Git Operations (`src/git_ops/snapshot_repo.py`)

**Purpose**: Manage the snapshot repository (Repo B).

**Key operations**:
1. `initialize()` - Clone repo or create if doesn't exist
2. `commit_snapshot()` - Copy files, git add, git commit
3. `_push_with_retry()` - Push with retry logic for concurrent commits

**Why it matters**: Automatic git integration with error handling and authentication.

---

## Code Examples

### Example 1: Direct Flattening (No API)

```python
from pathlib import Path
from src.engine.flattener.workbook import WorkbookFlattener

# Create flattener
flattener = WorkbookFlattener(include_evaluated=False)

# Flatten a file
result = flattener.flatten(
    input_file=Path("test.xlsx"),
    output_dir=Path("/tmp/output"),
)

# Access results
print(f"Snapshot: {result['snapshot_dir']}")
print(f"Manifest: {result['manifest'].to_dict()}")
```

### Example 2: Compare Snapshots

```python
from src.engine.differ.compare import SnapshotComparison
from src.engine.differ.diff_json import generate_json_diff

# Compare two snapshots
comparison = SnapshotComparison(
    Path("/tmp/snapshot-v1"),
    Path("/tmp/snapshot-v2"),
)

# Generate structured diff
diff = generate_json_diff(comparison)

# Show summary
for key, count in diff['summary'].items():
    if count > 0:
        print(f"{key}: {count}")

# Show changes
for change in diff['diff_json']:
    print(change)
```

### Example 3: Using the API

```bash
# Flatten a file
curl -X POST -F "file=@test.xlsx" \
  http://localhost:8000/api/v1/flatten

# Returns: {"job_id": "abc-123"}

# Poll for result
curl http://localhost:8000/api/v1/jobs/abc-123
```

---

## Where to Start Reading

### If you want to understand...

**How Excel files are flattened**:
1. Start: `src/engine/flattener/workbook.py` - `flatten()` method
2. Then: `src/engine/flattener/sheets.py` - `extract_sheet_data()`
3. Then: `src/engine/flattener/normalizer.py` - normalization rules

**How comparisons work**:
1. Start: `src/engine/differ/compare.py` - `SnapshotComparison` class
2. Then: `src/engine/differ/diff_json.py` - `generate_json_diff()`

**How the API works**:
1. Start: `src/api/main.py` - FastAPI app setup
2. Then: `src/api/routes/flatten.py` - Example endpoint
3. Then: `src/workers/tasks.py` - Worker implementation

**How jobs are queued**:
1. Start: `src/core/job_queue.py` - `JobQueueBackend` abstraction
2. Then: `src/workers/celery_app.py` - Celery configuration

**How git integration works**:
1. Start: `src/git_ops/snapshot_repo.py` - `SnapshotRepoManager`

---

## Common Patterns

### Pattern 1: Read Config Anywhere

```python
from src.core.config import get_settings

settings = get_settings()
print(settings.MAX_UPLOAD_BYTES)
```

### Pattern 2: Create Temp Directories

```python
from src.core.storage import create_temp_dir, cleanup_temp_dir

temp_dir = create_temp_dir(prefix="my-job")
try:
    # Use temp_dir
    ...
finally:
    cleanup_temp_dir(temp_dir)
```

### Pattern 3: Normalize Values

```python
from src.engine.flattener.normalizer import (
    normalize_formula,
    normalize_number,
    normalize_cell_value,
)

# Always normalize before writing to files
formula = normalize_formula(cell.value)
number = normalize_number(42.123456789)
```

### Pattern 4: Handle Errors Gracefully

```python
try:
    result = do_something()
except Exception as e:
    logger.exception(f"Failed: {e}")
    manifest.add_warning(f"Something failed: {e}")
    # Continue processing other items
```

---

## Next Steps

- Try running `snippets/test_functions.py` to see components in action
- Read through a single module completely to understand the style
- Modify normalization rules in `normalizer.py` and see the effect
- Add a new extraction feature (e.g., conditional formatting)

**Questions?** Check the code comments - most functions have docstrings explaining what they do!
