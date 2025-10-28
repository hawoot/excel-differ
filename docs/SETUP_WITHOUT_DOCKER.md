# Setup Without Docker

Quick guide to run Excel Diff Server without Docker.

## Prerequisites

- Python 3.10+
- Git
- LibreOffice (for XLSB conversion)
- Redis (optional - only for Celery backend)

## Quick Setup

### 1. Run Setup Script

```bash
chmod +x scripts/setup_local.sh
./scripts/setup_local.sh
```

This script will:
- Check Python version
- Check for LibreOffice, Git, Redis
- Create virtual environment
- Install dependencies
- Create .env file
- Guide you through configuration

### 2. Configure .env

Edit `.env` and set at minimum:

```bash
SNAPSHOT_REPO_URL=git@github.com:yourorg/excel-snapshots.git
QUEUE_BACKEND=celery  # or "multiprocessing" if no Redis
```

### 3. Start Services

**With Celery** (needs Redis):

```bash
# Terminal 1: API
source venv/bin/activate
python -m src.api.main

# Terminal 2: Worker
source venv/bin/activate
celery -A src.workers.celery_app worker --loglevel=info
```

**With Multiprocessing** (no Redis needed):

```bash
# Just one terminal!
source venv/bin/activate
python -m src.api.main
```

### 4. Test

```bash
curl http://localhost:8000/health
```

Open http://localhost:8000/docs

## Manual Setup (if script fails)

```bash
# 1. Create venv
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
nano .env  # Edit as needed

# 4. Run
python -m src.api.main
```

## Common Issues

**LibreOffice not found**: Update `CONVERTER_PATH` in `.env`
**Redis connection failed**: Set `QUEUE_BACKEND=multiprocessing` in `.env`
**Port in use**: Change `PORT=8080` in `.env`

See [SETUP_WITH_DOCKER.md](SETUP_WITH_DOCKER.md) for more details.
