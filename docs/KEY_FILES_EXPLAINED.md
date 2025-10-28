# Key Files Explained

**Overwhelmed by the code?** This guide explains the most important files you should know about.

## Start Here (3 Files)

### 1. `.env` - Configuration File
**Location**: Project root
**Purpose**: All settings in one place

```bash
# The most important settings:
QUEUE_BACKEND=multiprocessing    # Simple mode (no Redis)
SNAPSHOT_REPO_URL=               # Git repo (optional)
CONVERTER_PATH=/usr/bin/libreoffice  # For XLSB conversion
```

**You only need to edit this file to change behavior!**

### 2. `src/api/main.py` - The Server Entry Point
**Location**: `src/api/main.py`
**Purpose**: Starts the FastAPI server

This file creates the web server and hooks up all the endpoints.

**You don't need to edit this** - it just wires things together.

### 3. `src/engine/flattener/workbook.py` - The Core Logic
**Location**: `src/engine/flattener/workbook.py`
**Purpose**: Main orchestrator that flattens Excel files

**Key method**: `flatten(input_file) → snapshot_directory`

This is where the magic happens! It calls all the other modules.

---

## The "Flattening" Files (How Excel → Text Works)

### 4. `src/engine/flattener/normalizer.py`
**Purpose**: Makes data deterministic

**Key functions**:
- `normalize_formula()` - Uppercase functions, trim spaces
- `normalize_number()` - Limit to 15 significant digits
- `normalize_date()` - Consistent ISO8601 format

**Why it matters**: Same input always → same output (perfect for git)

### 5. `src/engine/flattener/sheets.py`
**Purpose**: Extracts sheet data (formulas, values, formats)

**What it creates**:
- `01.Sheet1.formulas.txt` - All formulas
- `01.Sheet1.values_hardcoded.txt` - All hard-coded values
- `01.Sheet1.cell_formats.txt` - Formatting info

**How it works**: Loops through every cell, normalizes values, writes to text files in row-major order.

### 6. `src/engine/flattener/vba.py`
**Purpose**: Extracts VBA modules

**What it creates**:
- `Module1.bas`, `Module2.bas`, etc.
- `vbaProject.bin` (raw binary, always kept)

**How it works**: Uses `oletools` library to parse VBA project.

---

## The "Comparison" Files (How Diffs Work)

### 7. `src/engine/differ/compare.py`
**Purpose**: Compare two flattened snapshots

**Key class**: `SnapshotComparison`

**How it works**:
1. Load both snapshots
2. Compare file hashes (quick check)
3. For changed files, diff line-by-line

### 8. `src/engine/differ/diff_json.py`
**Purpose**: Generate structured JSON diffs

**Output format**:
```json
{
  "category": "formula",
  "sheet": "Sheet1",
  "cell": "A1",
  "old": "=SUM(A2:A10)",
  "new": "=SUM(A2:A20)"
}
```

**How it works**: Parses formula/value files, detects changes, creates typed objects.

---

## The "API" Files (How HTTP Works)

### 9. `src/api/routes/flatten.py`
**Purpose**: Handle `POST /api/v1/flatten` requests

**What it does**:
1. Validate uploaded file
2. Submit job to queue
3. Return `job_id` immediately

**Pattern**: All endpoints follow this same pattern!

### 10. `src/api/routes/jobs.py`
**Purpose**: Handle `GET /api/v1/jobs/{job_id}` requests

**What it does**: Return job status (queued/running/success/failed) and results.

---

## The "Worker" Files (How Background Processing Works)

### 11. `src/workers/tasks.py`
**Purpose**: Actual background job implementations

**Key functions**:
- `flatten_task()` - Runs flattening in background
- `extract_task()` - Flattens + commits to git
- `compare_task()` - Compares two snapshots

**How it works**: Celery (or multiprocessing) calls these functions.

### 12. `src/core/job_queue.py`
**Purpose**: Abstraction so we can use Celery OR multiprocessing

**Key classes**:
- `CeleryBackend` - Uses Redis + Celery
- `MultiprocessingBackend` - Simple in-process queue

**Why it matters**: One config flag (`QUEUE_BACKEND`) switches between them!

---

## The "Git" Files (How Repository Integration Works)

### 13. `src/git_ops/snapshot_repo.py`
**Purpose**: Manage git repository operations

**Key class**: `SnapshotRepoManager`

**Key methods**:
- `initialize()` - Clone repo or create if doesn't exist
- `commit_snapshot()` - Copy files, git add, git commit, git push

**How it works**: Uses GitPython library to automate git commands.

---

## The "Config" Files

### 14. `src/core/config.py`
**Purpose**: Load settings from `.env` file

**How it works**: Uses Pydantic to load and validate environment variables.

All modules import this to get settings:
```python
from src.core.config import get_settings
settings = get_settings()
print(settings.MAX_UPLOAD_BYTES)
```

### 15. `src/core/storage.py`
**Purpose**: Helper functions for file operations

**Key functions**:
- `create_temp_dir()` - Make temp directory
- `cleanup_temp_dir()` - Remove temp directory
- `create_zip_archive()` - Create ZIP file
- `get_file_hash()` - Calculate SHA256

**Why it matters**: Used everywhere to handle files safely.

---

## Files You Can Safely Ignore (For Now)

These are important but you don't need to understand them immediately:

- `src/engine/flattener/converter.py` - XLSB→XLSM conversion (uses LibreOffice)
- `src/engine/flattener/metadata.py` - Extracts workbook metadata
- `src/engine/flattener/manifest.py` - Generates manifest.json
- `src/engine/flattener/tables.py` - Table extraction (placeholder)
- `src/engine/flattener/charts.py` - Chart extraction (placeholder)
- `src/engine/flattener/styles.py` - Style extraction (placeholder)
- `src/workers/celery_app.py` - Celery configuration
- `src/api/models.py` - Pydantic request/response models

---

## The Data Flow

Here's how a file travels through the system:

```
1. User uploads Excel file
   ↓
2. FastAPI (flatten.py) validates it
   ↓
3. Job queue (job_queue.py) queues it
   ↓
4. Worker (tasks.py) picks it up
   ↓
5. Flattener (workbook.py) orchestrates:
   - normalizer.py normalizes data
   - sheets.py extracts sheets
   - vba.py extracts VBA
   - etc.
   ↓
6. Result stored, user can download
```

---

## How to Explore

**Start simple**:
1. Read `src/engine/flattener/normalizer.py` (simple pure functions)
2. Read `src/engine/flattener/workbook.py` (see how it all connects)
3. Read `src/api/routes/flatten.py` (see API pattern)

**Then go deeper**:
4. Read `src/engine/flattener/sheets.py` (detailed extraction)
5. Read `src/engine/differ/compare.py` (comparison logic)
6. Read `src/core/job_queue.py` (async pattern)

**Pro tip**: Each file has docstrings at the top explaining what it does!

---

## Quick Reference

| I want to... | Look at this file |
|--------------|-------------------|
| Change how formulas are normalized | `src/engine/flattener/normalizer.py` |
| Add new sheet extraction | `src/engine/flattener/sheets.py` |
| Change API behavior | `src/api/routes/*.py` |
| Modify git operations | `src/git_ops/snapshot_repo.py` |
| Change configuration | `.env` file (not code!) |
| Add new API endpoint | Create new file in `src/api/routes/` |
| Change diff logic | `src/engine/differ/diff_json.py` |

---

## Next Steps

1. ✅ You now know what each key file does
2. ✅ Pick one file and read it completely
3. ✅ Try modifying something (e.g., change `normalize_formula`)
4. ✅ Run `python snippets/test_functions.py` to see the effect
5. ✅ Read [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md) for deeper understanding

**Remember**: You don't need to understand everything at once. Pick one area and go deep!
