# Getting Started with Excel Diff Server

Welcome! This guide will help you understand and use the Excel Diff Server.

## What is This?

The Excel Diff Server transforms Excel files into **git-friendly text snapshots** so you can:
- Track Excel changes in version control (like you do with code)
- See exactly what changed between versions (formulas, values, VBA)
- Automate Excel file comparisons at scale

## 5-Minute Quick Start

### Option 1: Docker (Easiest)

```bash
# 1. Configure
cp .env.example .env
nano .env  # Set SNAPSHOT_REPO_URL

# 2. Start
cd docker && docker-compose up -d

# 3. Test
curl http://localhost:8000/health
open http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# 1. Run setup
./scripts/setup_local.sh

# 2. Start server
source venv/bin/activate
python -m src.api.main

# 3. Test
curl http://localhost:8000/health
```

## Understanding the System

### The Big Picture

```
Excel File (binary) → Flattener → Text Files (git-friendly)
                                      ↓
                              Snapshot Repository
                                      ↓
                              Compare Versions → Structured Diff
```

### What Gets Extracted?

From any Excel file, the system extracts:
- ✅ **Formulas** (normalized, uppercase functions)
- ✅ **Values** (hard-coded and optionally evaluated)
- ✅ **VBA Code** (modules, classes, forms)
- ✅ **Cell Formats** (fonts, colors, number formats)
- ✅ **Structure** (sheet order, visibility, merged cells)
- ✅ **Comments, Validations, Tables** (and more)

Everything is saved as **text files** in a **deterministic order**.

### Example Output

When you flatten `revenue.xlsx`, you get:

```
revenue-snapshot-20251027T120000Z-abcd1234/
├── manifest.json              # Complete metadata
├── original/workbook.xlsx     # Original file
├── workbook/
│   ├── metadata.txt          # Author, dates
│   └── structure.txt         # Sheet list
├── sheets/
│   ├── 01.Summary.formulas.txt
│   ├── 01.Summary.values_hardcoded.txt
│   └── 02.Details.formulas.txt
└── vba/
    ├── Module1.bas
    └── vbaProject.bin
```

All text files, perfect for git!

## Key Concepts

### 1. Normalization

The system **normalizes** everything so the same input always produces the same output:

```python
# Formulas: uppercase, trimmed
"=sum(a1:a10)" → "=SUM(A1:A10)"

# Numbers: 15 significant digits
123.456789012345678 → "123.456789012346"

# Dates: ISO8601 format
datetime(...) → "2025-10-27T00:00:00Z"
```

**Why?** So git can show you real changes, not formatting differences.

### 2. Async Jobs

All operations return a `job_id` immediately:

```bash
# Submit job
curl -X POST -F "file=@test.xlsx" http://localhost:8000/api/v1/flatten
# → {"job_id": "abc-123"}

# Poll for result
curl http://localhost:8000/api/v1/jobs/abc-123
# → {"status": "success", "result": {...}}
```

**Why?** Large Excel files can take time. This lets you submit many files in parallel.

### 3. Two Repositories

- **Repo A (Origin)**: Where users edit Excel files
- **Repo B (Snapshot)**: Where server commits flattened snapshots

**Why separate?** Keep noisy snapshots out of your main repo.

## Three Main Operations

### 1. Extract (for CI/CD)

**Use case**: Automatically snapshot Excel files when they're committed.

```bash
curl -X POST -F "file=@revenue.xlsb" \
  -F "origin_repo=git@github.com:org/repo.git" \
  -F "origin_commit=abc123" \
  http://localhost:8000/api/v1/extract
```

Result: Snapshot committed to Repo B with git metadata.

### 2. Flatten (ad-hoc)

**Use case**: Get a flattened snapshot as a downloadable archive.

```bash
curl -X POST -F "file=@report.xlsm" \
  http://localhost:8000/api/v1/flatten
```

Result: ZIP file with all flattened files.

### 3. Compare (on-demand)

**Use case**: See what changed between two Excel files.

```bash
curl -X POST -F "file_a=@old.xlsx" -F "file_b=@new.xlsx" \
  http://localhost:8000/api/v1/compare
```

Result: Structured JSON diff showing every change.

## Helpful Resources

### For Learning

1. **Start here**: [CODE_WALKTHROUGH.md](docs/CODE_WALKTHROUGH.md)
   - Understand how the code works
   - See request flow diagrams
   - Learn key components

2. **Try examples**: [snippets/](snippets/)
   - `test_functions.py` - Direct function calls
   - `test_functions.ipynb` - Jupyter notebook
   - `test_api.sh` - API testing script

3. **Read docs**: [docs/](docs/)
   - Setup guides (Docker & non-Docker)
   - Git authentication
   - API usage examples

### For Setup

- **Docker**: [docs/SETUP_WITH_DOCKER.md](docs/SETUP_WITH_DOCKER.md)
- **Local**: [docs/SETUP_WITHOUT_DOCKER.md](docs/SETUP_WITHOUT_DOCKER.md)
- **Git Auth**: [docs/GIT_AUTHENTICATION.md](docs/GIT_AUTHENTICATION.md)

### For Usage

- **API Reference**: http://localhost:8000/docs (Swagger UI)
- **Code Examples**: [snippets/README.md](snippets/README.md)
- **Requirements**: [docs/Differ Requirements.md](docs/Differ%20Requirements.md)

## Common Questions

### Q: Do I need Docker?

**No!** You can run locally with Python. Docker just makes it easier.

### Q: Do I need Redis?

**No!** Set `QUEUE_BACKEND=multiprocessing` in `.env` to use simpler in-process queuing.

### Q: How do I authenticate with Git?

Two options:
1. **SSH keys** (recommended): Add your key to GitHub/GitLab
2. **HTTPS token**: Embed token in `SNAPSHOT_REPO_URL`

See [GIT_AUTHENTICATION.md](docs/GIT_AUTHENTICATION.md) for details.

### Q: What if I don't want to use a Git repo?

Just leave `SNAPSHOT_REPO_URL` empty. You can still use `/flatten` and `/compare` endpoints.

### Q: Can it handle large files?

Yes! Default limit is 200MB. Configure `MAX_UPLOAD_BYTES` in `.env`.
Processing happens in background workers with 15-minute timeout.

### Q: What Excel formats are supported?

- ✅ `.xlsx` (Excel 2007+)
- ✅ `.xlsm` (Excel with macros)
- ✅ `.xlsb` (Binary Excel - auto-converted)
- ⚠️ `.xls` (Legacy Excel - experimental)

## Next Steps

### 1. Get It Running

Follow quick start above (5 minutes)

### 2. Try It Out

```bash
# Create a test Excel file
python -c "
from openpyxl import Workbook
wb = Workbook()
ws = wb.active
ws['A1'] = '=SUM(1,2,3)'
wb.save('test.xlsx')
"

# Flatten it
curl -X POST -F "file=@test.xlsx" http://localhost:8000/api/v1/flatten
```

### 3. Explore the Code

```bash
# Run test functions
python snippets/test_functions.py

# Or use the notebook
jupyter notebook snippets/test_functions.ipynb
```

### 4. Read the Walkthrough

Open [docs/CODE_WALKTHROUGH.md](docs/CODE_WALKTHROUGH.md) to understand how it all works.

### 5. Integrate with Your Workflow

- Add to your Git hooks
- Integrate with CI/CD pipeline
- Build a UI on top of the API
- Customize extraction logic

## Getting Help

### Check Logs

```bash
# Docker
docker-compose logs -f api
docker-compose logs -f worker

# Local
tail -f /tmp/excel-differ/*.log
```

### Test Components

```bash
# Test health
curl http://localhost:8000/health

# Test LibreOffice
libreoffice --version

# Test Redis
redis-cli ping
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Port in use | Change `PORT` in `.env` |
| LibreOffice not found | Update `CONVERTER_PATH` in `.env` |
| Git auth failed | Check [GIT_AUTHENTICATION.md](docs/GIT_AUTHENTICATION.md) |
| Import errors | `source venv/bin/activate` |

## Contributing & Customization

The code is well-structured and documented. To customize:

1. **Add new extraction**: Edit `src/engine/flattener/sheets.py`
2. **Change normalization**: Edit `src/engine/flattener/normalizer.py`
3. **Add API endpoint**: Create new file in `src/api/routes/`
4. **Modify diff logic**: Edit `src/engine/differ/diff_json.py`

All modules have docstrings and type hints!

---

**Happy diffing! 🎉**

Questions? Check the docs folder or read the code comments - they're detailed!
