# Excel Diff Server - Docker Setup Guide

This guide will help you set up and run the Excel Diff Server using Docker.

## Prerequisites

- Docker (20.10+) and Docker Compose (2.0+)
- Git (for snapshot repository access)
- 2GB+ free disk space

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd excel-differ
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and configure at minimum:

```bash
# Snapshot repository where flattened files will be committed
SNAPSHOT_REPO_URL=git@github.com:yourorg/excel-snapshots.git

# Git user info for commits
GIT_USER_NAME=Excel Diff Server
GIT_USER_EMAIL=excel-diff@example.com
```

See [GIT_AUTHENTICATION.md](GIT_AUTHENTICATION.md) for authentication setup.

### 3. Start the Stack

```bash
cd docker
docker-compose up -d
```

This starts:
- **Redis** (message broker) on port 6379
- **API Server** (FastAPI) on port 8000
- **Celery Worker** (background processor)

### 4. Verify Setup

Check all services are running:

```bash
docker-compose ps
```

Check health:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "queue_backend": "celery",
  "libreoffice_available": true,
  "libreoffice_version": "LibreOffice 7.x.x.x"
}
```

### 5. Access the API

- **Swagger UI (interactive docs)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

## Git Authentication in Docker

### SSH Keys (Recommended)

To use SSH authentication with your snapshot repository:

1. Generate SSH key (if you don't have one):

```bash
ssh-keygen -t ed25519 -C "excel-diff@example.com"
```

2. Add public key to GitHub/GitLab

3. Uncomment the SSH volume mount in `docker-compose.yml`:

```yaml
volumes:
  - ~/.ssh:/root/.ssh:ro
```

4. Restart containers:

```bash
docker-compose down
docker-compose up -d
```

### HTTPS with Token

Alternatively, include token in `SNAPSHOT_REPO_URL`:

```bash
SNAPSHOT_REPO_URL=https://YOUR_TOKEN@github.com/yourorg/excel-snapshots.git
```

See [GIT_AUTHENTICATION.md](GIT_AUTHENTICATION.md) for detailed instructions.

## Common Operations

### View Logs

All services:
```bash
docker-compose logs -f
```

Specific service:
```bash
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f redis
```

### Restart Services

```bash
docker-compose restart
```

### Stop Services

```bash
docker-compose down
```

### Rebuild After Code Changes

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Scale Workers

Edit `docker-compose.yml`:

```yaml
worker:
  # ...
  environment:
    - WORKER_CONCURRENCY=8  # Increase concurrency
```

Or run multiple worker containers:

```bash
docker-compose up -d --scale worker=3
```

## Volume Management

Docker volumes store persistent data:

- `snapshot-repo`: Cloned snapshot repository
- `temp-storage`: Temporary job artifacts
- `redis-data`: Redis persistence

### Backup Volumes

```bash
docker run --rm -v excel-differ_snapshot-repo:/data -v $(pwd):/backup ubuntu tar czf /backup/snapshot-repo-backup.tar.gz /data
```

### Clear Temporary Data

```bash
docker-compose down
docker volume rm excel-differ_temp-storage
docker-compose up -d
```

## Troubleshooting

### Port Already in Use

If port 8000 or 6379 is already in use, edit `docker-compose.yml`:

```yaml
api:
  ports:
    - "8080:8000"  # Change host port
```

### Git Authentication Failures

Check logs:
```bash
docker-compose logs worker
```

Common issues:
- SSH key not mounted correctly
- Token expired or invalid
- Repository doesn't exist

See [GIT_AUTHENTICATION.md](GIT_AUTHENTICATION.md) for solutions.

### LibreOffice Not Working

Check LibreOffice is available:

```bash
docker-compose exec api libreoffice --version
```

If missing, rebuild image:

```bash
docker-compose build --no-cache
```

### Worker Not Processing Jobs

Check worker is running:

```bash
docker-compose ps worker
docker-compose logs worker
```

Check Redis connection:

```bash
docker-compose exec api redis-cli -h redis ping
```

### Out of Disk Space

Check volume sizes:

```bash
docker system df -v
```

Clean up old data:

```bash
# Remove old containers and images
docker system prune -a

# Remove specific volumes
docker volume ls
docker volume rm excel-differ_temp-storage
```

## Production Considerations

For production deployment:

1. **Use secrets management** for tokens (Docker secrets, Kubernetes secrets)
2. **Set resource limits** in `docker-compose.yml`:

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 2G
```

3. **Configure CORS** in `.env`:

```bash
# Edit src/api/main.py to restrict origins
```

4. **Add authentication** to API endpoints

5. **Use external Redis** for high availability

6. **Set up monitoring** (Prometheus, Grafana)

7. **Configure log rotation**

## Next Steps

- Read [API_USAGE.md](API_USAGE.md) for API examples
- Read [GIT_AUTHENTICATION.md](GIT_AUTHENTICATION.md) for auth setup
- See the [Requirements Document](../docs/Differ%20Requirements.md) for full specifications
