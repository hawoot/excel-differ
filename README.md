# Excel Diff Server

> **🚀 Confused? Start with [QUICKSTART.md](QUICKSTART.md) - Get running in 2 minutes!**
>
> **📖 Want to understand the code? Read [docs/CODE_WALKTHROUGH.md](docs/CODE_WALKTHROUGH.md)**

A powerful server for flattening Excel workbooks into human- and git-diffable text snapshots, and comparing Excel files at scale.

## What It Does

The Excel Diff Server transforms binary Excel files (.xlsb, .xlsm, .xlsx) into deterministic, text-based snapshots that can be:

- **Committed to Git** - Track changes to Excel files just like code
- **Diffed meaningfully** - See exactly what formulas, values, or VBA changed
- **Compared on-demand** - Get structured JSON diffs between any two workbooks
- **Processed asynchronously** - Handle large files with background workers

## Key Features

✅ **Complete Extraction**: Formulas, values, VBA, charts, pivots, tables, formats, and more
✅ **Deterministic Output**: Same input always produces same output (perfect for git)
✅ **Async Processing**: Queue-based architecture (Celery + Redis or multiprocessing)
✅ **Git Integration**: Auto-commit snapshots to a repository with full metadata
✅ **Structured Diffs**: Type d JSON output (formula changes, value changes, etc.)
✅ **XLSB Support**: Automatic conversion using LibreOffice
✅ **Docker Ready**: Complete Docker Compose stack included
✅ **Flexible Deployment**: Works with or without Docker, with or without Redis

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone repo
git clone <your-repo-url>
cd excel-differ

# Configure
cp .env.example .env
# Edit .env with your snapshot repo URL

# Start
cd docker
docker-compose up -d

# Access API
open http://localhost:8000/docs
```

See [docs/SETUP_WITH_DOCKER.md](docs/SETUP_WITH_DOCKER.md) for details.

### Option 2: Local Development

```bash
# Clone repo
git clone <your-repo-url>
cd excel-differ

# Run setup script
chmod +x scripts/setup_local.sh
./scripts/setup_local.sh

# Start server
source venv/bin/activate
python -m src.api.main
```

See [docs/SETUP_WITHOUT_DOCKER.md](docs/SETUP_WITHOUT_DOCKER.md) for details.

## Architecture

```
┌─────────────┐      POST /extract     ┌──────────────┐
│  Git Hook   │ ──────────────────────>│   FastAPI    │
│  or Client  │                        │  API Server  │
└─────────────┘                        └──────┬───────┘
                                              │
                                              ▼
┌─────────────┐                        ┌──────────────┐
│ Snapshot    │ <───── commit ─────────│    Celery    │
│ Repo (Git)  │                        │    Worker    │
└─────────────┘                        └──────┬───────┘
                                              │
                                              ▼
                                        ┌──────────────┐
                                        │   Flattener  │
                                        │    Engine    │
                                        └──────────────┘
```

### Components

- **FastAPI Server**: REST API endpoints (`/extract`, `/flatten`, `/compare`)
- **Celery Workers**: Background job processing
- **Redis**: Message broker (or multiprocessing fallback)
- **Flattener Engine**: Extracts Excel files into deterministic text snapshots
- **Diff Engine**: Compares snapshots and generates structured diffs
- **Git Operations**: Commits snapshots to configured repository

## API Endpoints

### POST /api/v1/extract

Extract and commit a workbook to the snapshot repository.

```bash
curl -X POST -F "file=@revenue.xlsb" \
  -F "origin_repo=git@github.com:org/repo.git" \
  -F "origin_commit=abc123" \
  http://localhost:8000/api/v1/extract
```

Returns: `{"status": "accepted", "job_id": "..."}`

### POST /api/v1/flatten

Flatten a workbook to a downloadable archive.

```bash
curl -X POST -F "file=@report.xlsm" \
  http://localhost:8000/api/v1/flatten
```

### POST /api/v1/compare

Compare two workbooks (or snapshots).

```bash
curl -X POST \
  -F "file_a=@old.xlsx" \
  -F "file_b=@new.xlsx" \
  http://localhost:8000/api/v1/compare
```

Returns structured JSON diff with:
- Sheet changes (added, removed)
- Formula changes (cell-by-cell)
- Value changes (hard-coded and evaluated)
- VBA changes
- Format changes

### GET /api/v1/jobs/{job_id}

Poll for job status and results.

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

See [docs/API_USAGE.md](docs/API_USAGE.md) for full API documentation.

## Snapshot Structure

Flattened snapshots follow a deterministic folder structure:

```
workbook-snapshot-20251027T120000Z-abcd1234/
├── manifest.json           # Canonical manifest
├── original/
│   └── workbook.xlsb      # Original file
├── workbook/
│   ├── metadata.txt       # Author, dates, version
│   ├── structure.txt      # Sheet order, visibility
│   └── defined_names.txt  # Named ranges
├── sheets/
│   ├── 01.Sheet1.formulas.txt
│   ├── 01.Sheet1.values_hardcoded.txt
│   ├── 01.Sheet1.cell_formats.txt
│   └── ...
├── vba/
│   ├── vbaProject.bin     # Raw VBA project
│   ├── Module1.bas
│   └── ...
├── tables/
├── charts/
├── pivots/
└── styles/
```

All files are:
- **Text-based** (UTF-8, LF line endings)
- **Normalized** (uppercase functions, canonical formatting)
- **Sorted** (row-major cell order for consistency)

## Configuration

Key environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `SNAPSHOT_REPO_URL` | Git repo for snapshots | (required) |
| `QUEUE_BACKEND` | `celery` or `multiprocessing` | `celery` |
| `CONVERTER_PATH` | Path to LibreOffice | `/usr/bin/libreoffice` |
| `MAX_UPLOAD_BYTES` | Max file size | 200 MB |
| `EXTRACTION_TIMEOUT_SECONDS` | Job timeout | 900 (15 min) |
| `RESULT_TTL_SECONDS` | Result retention | 36000 (10 hours) |

## Use Cases

### 1. Git Hook Integration

Automatically snapshot Excel files on commit:

```bash
# In your Git hook (pre-commit or post-commit)
for file in $(git diff --name-only | grep -E '\.(xlsb|xlsm|xlsx)$'); do
  curl -X POST -F "file=@$file" \
    -F "origin_repo=$(git remote get-url origin)" \
    -F "origin_commit=$(git rev-parse HEAD)" \
    http://excel-diff-server/api/v1/extract
done
```

### 2. CI/CD Pipeline

```yaml
# .github/workflows/excel-diff.yml
steps:
  - name: Extract Excel Files
    run: |
      for file in *.xlsb; do
        curl -X POST -F "file=@$file" \
          http://excel-diff-server/api/v1/extract
      done
```

### 3. Ad-Hoc Comparison

```bash
# Compare two versions of a file
curl -X POST \
  -F "file_a=@Q1-report.xlsm" \
  -F "file_b=@Q2-report.xlsm" \
  http://localhost:8000/api/v1/compare
```

## Development

### Project Structure

```
excel-differ/
├── src/
│   ├── api/            # FastAPI endpoints
│   ├── core/           # Config, job queue, storage
│   ├── engine/
│   │   ├── flattener/  # Excel extraction
│   │   └── differ/     # Comparison engine
│   ├── git_ops/        # Git repository operations
│   └── workers/        # Celery tasks
├── docker/             # Docker setup
├── scripts/            # Setup scripts
├── tests/              # Unit tests
└── docs/               # Documentation
```

### Running Tests

```bash
source venv/bin/activate
pytest
```

### Code Style

```bash
black src/ tests/
flake8 src/ tests/
```

## Troubleshooting

### Git Authentication Issues

See [docs/GIT_AUTHENTICATION.md](docs/GIT_AUTHENTICATION.md) for:
- SSH key setup
- Personal access token usage
- Common authentication errors

### LibreOffice Not Found

**Docker**: Rebuild image
```bash
docker-compose build --no-cache
```

**Local**: Install LibreOffice
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice libreoffice-calc

# macOS
brew install libreoffice
```

### Jobs Stuck in "queued"

Check worker is running:

**Docker**:
```bash
docker-compose logs worker
```

**Local**:
```bash
celery -A src.workers.celery_app worker --loglevel=info
```

## Requirements

- Python 3.10+ (3.11 recommended)
- LibreOffice (for XLSB conversion)
- Git
- Redis (optional, for Celery backend)

## Documentation

- [Complete Requirements](docs/Differ%20Requirements.md) - Full specification
- [Docker Setup](docs/SETUP_WITH_DOCKER.md) - Docker deployment guide
- [Local Setup](docs/SETUP_WITHOUT_DOCKER.md) - Non-Docker setup
- [Git Authentication](docs/GIT_AUTHENTICATION.md) - Auth configuration
- [API Usage](docs/API_USAGE.md) - API examples and reference

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines]

## Support

For issues, questions, or contributions, please [open an issue](your-repo-url/issues).
