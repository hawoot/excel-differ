# Excel Diff Server Architecture

## Overview

The Excel Diff Server uses a **job queue architecture** to process long-running tasks asynchronously. This document explains how the system works and answers common setup questions.

## System Components

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   FastAPI    │────────▶│  Job Queue   │────────▶│   Workers    │
│  API Server  │         │   Backend    │         │  (Celery or  │
│ (HTTP/REST)  │         │(Celery/Multi)│         │ Multiproc)   │
└──────────────┘         └──────────────┘         └──────────────┘
       │                        │                          │
       │                        │                          │
       ▼                        ▼                          ▼
  ┌─────────────────────────────────────────────────────────┐
  │              Shared Storage (File System)              │
  │   - Uploaded files                                      │
  │   - Job metadata (JSON files)                           │
  │   - Generated snapshots                                 │
  │   - Archives (ZIP/TAR.GZ)                               │
  └─────────────────────────────────────────────────────────┘
```

## How It Works

### 1. API Server (FastAPI)

- **Role**: Receives HTTP requests, validates input, returns job IDs
- **Endpoints**:
  - `POST /api/v1/flatten` - Flatten Excel file to archive
  - `POST /api/v1/compare` - Compare two Excel files
  - `POST /api/v1/extract` - Flatten and commit to Git repo
  - `GET /api/v1/jobs/{job_id}` - Poll for job status/results

**Flow**:
1. User uploads file via HTTP
2. API validates file size and parameters
3. API submits job to queue, gets `job_id`
4. API returns `202 Accepted` with `job_id`
5. User polls `GET /jobs/{job_id}` until status is "success" or "failed"

### 2. Job Queue Backend

The system supports **two backends**:

#### Option A: Multiprocessing (Simple Setup)

```
┌──────────────┐
│  API Server  │
│   Process    │
│              │
│  ┌────────┐  │
│  │ Worker │  │  ← Background thread pool
│  │ Thread │  │
│  └────────┘  │
└──────────────┘
```

- **When to use**: Development, simple setups, no Redis available
- **Config**: `QUEUE_BACKEND=multiprocessing`
- **Requirements**: None (built into Python)
- **Limitations**:
  - All workers run in same process as API server
  - Can't scale beyond one machine
  - Job state stored in JSON files on disk

**How it works**:
- Uses Python's `ProcessPoolExecutor`
- Creates 4 worker threads by default (configurable via `WORKER_CONCURRENCY`)
- Job metadata saved to `/tmp/excel-differ/jobs/{job_id}.json`
- **Everything runs on the same server as the API**

#### Option B: Celery + Redis (Production Setup)

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  API Server  │────────▶│    Redis     │◀────────│Celery Worker │
│   Process    │         │   (Broker)   │         │   Process    │
└──────────────┘         └──────────────┘         └──────────────┘
```

- **When to use**: Production, high load, need scalability
- **Config**: `QUEUE_BACKEND=celery`
- **Requirements**: Redis server running
- **Benefits**:
  - Workers can run on separate machines
  - Better reliability and retry handling
  - Redis manages job state (faster than disk)
  - Can scale horizontally (add more workers)

**How it works**:
1. API submits job to Redis queue
2. Celery worker picks up job from Redis
3. Worker processes job, stores result in Redis
4. API queries Redis to get job status

### 3. Workers (Task Execution)

Workers execute the actual processing:

- **Extract**: Flatten Excel + commit to Git repo
- **Flatten**: Flatten Excel + create ZIP/TAR.GZ archive
- **Compare**: Compare two Excel files, generate diff

All workers use the same code in [src/workers/tasks.py](../src/workers/tasks.py):
- `extract_task_sync()` - Can be called directly (multiprocessing) or via Celery
- `flatten_task_sync()` - Can be called directly (multiprocessing) or via Celery
- `compare_task_sync()` - Can be called directly (multiprocessing) or via Celery

## Can Redis and Celery Run on the Same Server?

**YES!** This is the most common setup.

### Typical Deployment Options:

#### Option 1: Everything on One Server (Recommended for Start)

```
┌─────────────────────────────────────┐
│         Single Server               │
│                                     │
│  ┌──────────────┐                  │
│  │  API Server  │ (port 8000)      │
│  │  (FastAPI)   │                  │
│  └──────────────┘                  │
│         │                           │
│         ▼                           │
│  ┌──────────────┐                  │
│  │    Redis     │ (port 6379)      │
│  └──────────────┘                  │
│         │                           │
│         ▼                           │
│  ┌──────────────┐                  │
│  │Celery Worker │                  │
│  │  (4 threads) │                  │
│  └──────────────┘                  │
└─────────────────────────────────────┘
```

**How to start**:
```bash
# Terminal 1: Start Redis (if not running)
redis-server

# Terminal 2: Start API server
python -m src.api.main

# Terminal 3: Start Celery worker
celery -A src.workers.celery_app worker --loglevel=info
```

**Docker Compose** (even easier):
```bash
docker-compose up
```

This starts all three services in containers on the same machine!

#### Option 2: Distributed (Scale Later)

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Server 1   │         │   Server 2   │         │   Server 3   │
│  API Server  │────────▶│    Redis     │◀────────│Celery Worker │
│              │         │              │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
```

**When to use**: High load, need redundancy, horizontal scaling

**Configuration**:
```bash
# Server 1 (.env on API server)
CELERY_BROKER_URL=redis://server2-hostname:6379/0

# Server 3 (.env on worker)
CELERY_BROKER_URL=redis://server2-hostname:6379/0
```

#### Option 3: Multiple Workers, Same Server

```
┌─────────────────────────────────────┐
│         Single Server               │
│                                     │
│  ┌──────────────┐                  │
│  │  API Server  │                  │
│  └──────────────┘                  │
│         │                           │
│  ┌──────────────┐                  │
│  │    Redis     │                  │
│  └──────────────┘                  │
│         │                           │
│    ┌────┴────┬────────┐            │
│    ▼         ▼        ▼            │
│  ┌────┐   ┌────┐   ┌────┐         │
│  │Wkr1│   │Wkr2│   │Wkr3│         │
│  └────┘   └────┘   └────┘         │
└─────────────────────────────────────┘
```

**Start multiple workers**:
```bash
# Terminal 1
celery -A src.workers.celery_app worker --loglevel=info -n worker1@%h

# Terminal 2
celery -A src.workers.celery_app worker --loglevel=info -n worker2@%h

# Terminal 3
celery -A src.workers.celery_app worker --loglevel=info -n worker3@%h
```

## Choosing the Right Setup

| Scenario | Recommended Setup | Why |
|----------|------------------|-----|
| **Local development** | Multiprocessing | No Redis needed, simpler |
| **Work environment (no admin)** | Multiprocessing | Can't install Redis |
| **Shared server (can install Redis)** | Celery + Redis, same server | Better reliability |
| **Production, low-medium load** | Celery + Redis, same server | Good balance |
| **Production, high load** | Celery + Redis, separate workers | Horizontal scaling |
| **Docker available** | Docker Compose | Everything configured |

## Configuration Files

### .env Configuration

#### For Multiprocessing:
```bash
# Simple setup - no Redis needed
QUEUE_BACKEND=multiprocessing
WORKER_CONCURRENCY=4
```

#### For Celery (same server):
```bash
# Redis running on localhost
QUEUE_BACKEND=celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
WORKER_CONCURRENCY=4
```

#### For Celery (separate servers):
```bash
# API server and workers point to Redis server
QUEUE_BACKEND=celery
CELERY_BROKER_URL=redis://your-redis-server:6379/0
CELERY_RESULT_BACKEND=redis://your-redis-server:6379/0
```

## Job Status Flow

```
User Upload
    │
    ▼
┌─────────┐
│ QUEUED  │ ← Job created, waiting for worker
└─────────┘
    │
    ▼
┌─────────┐
│ RUNNING │ ← Worker picked up job, processing
└─────────┘
    │
    ├─────────────┬─────────────┐
    ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ SUCCESS │  │ FAILED  │  │ TIMEOUT │
└─────────┘  └─────────┘  └─────────┘
```

## Common Issues & Solutions

### Issue: "API returns job_id but job never completes"

**Cause**: Workers not running (or not working)

**Solution**:
- **Multiprocessing**: Check API server logs for errors
- **Celery**: Make sure worker process is running (`celery -A src.workers.celery_app worker`)

### Issue: "Connection refused to Redis"

**Cause**: Redis not running

**Solution**:
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not, start Redis
redis-server
```

### Issue: "ImportError: No module named 'celery'"

**Cause**: Celery not installed

**Solution**:
```bash
pip install celery redis
# Or
pip install -r requirements.txt
```

## Performance Tuning

### Multiprocessing Backend

```python
# .env
WORKER_CONCURRENCY=8  # Increase for more CPU cores
```

**Rule of thumb**: Set to number of CPU cores

### Celery Backend

```bash
# Start worker with more threads
celery -A src.workers.celery_app worker --concurrency=8

# Or set in .env
WORKER_CONCURRENCY=8
```

**Rule of thumb**:
- CPU-bound tasks (Excel processing): 1x CPU cores
- I/O-bound tasks (Git operations): 2-4x CPU cores

## Summary

**Key Takeaways**:

1. ✅ **Redis and Celery CAN run on the same server** - this is very common!
2. ✅ **Multiprocessing is perfect for simple setups** - no Redis needed
3. ✅ **Start simple, scale later** - begin with one server, add workers as needed
4. ✅ **Docker Compose is the easiest** - everything configured automatically
5. ✅ **All components work together via shared storage** - filesystem and Redis/JSON

**Quick Start**:
- Development → Use `QUEUE_BACKEND=multiprocessing`
- Production (same server) → Use `QUEUE_BACKEND=celery` with local Redis
- Production (distributed) → Use `QUEUE_BACKEND=celery` with remote Redis
