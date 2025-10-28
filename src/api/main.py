"""
FastAPI main application.
Excel Diff Server - REST API for flattening and comparing Excel workbooks.
"""
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.api.routes import extract, flatten, compare, jobs, snapshots

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Excel Diff Server - Flatten and compare Excel workbooks",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.LOG_LEVEL == "DEBUG" else None,
        },
    )


# Include routers
app.include_router(
    extract.router,
    prefix=settings.API_V1_PREFIX,
    tags=["extract"],
)

app.include_router(
    flatten.router,
    prefix=settings.API_V1_PREFIX,
    tags=["flatten"],
)

app.include_router(
    compare.router,
    prefix=settings.API_V1_PREFIX,
    tags=["compare"],
)

app.include_router(
    jobs.router,
    prefix=settings.API_V1_PREFIX,
    tags=["jobs"],
)

app.include_router(
    snapshots.router,
    prefix=settings.API_V1_PREFIX,
    tags=["snapshots"],
)


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from src.engine.flattener.converter import check_libreoffice_available, get_libreoffice_version

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "queue_backend": settings.QUEUE_BACKEND,
        "libreoffice_available": check_libreoffice_available(),
        "libreoffice_version": get_libreoffice_version(),
    }


@app.get("/version")
async def version():
    """Version information endpoint."""
    from src.engine.flattener.converter import get_libreoffice_version

    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "extractor_version": "0.1.0",
        "libreoffice_version": get_libreoffice_version(),
        "queue_backend": settings.QUEUE_BACKEND,
    }


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Queue backend: {settings.QUEUE_BACKEND}")
    logger.info(f"Snapshot repo: {settings.SNAPSHOT_REPO_URL or '(local only)'}")

    # Initialize snapshot repo
    try:
        from src.git_ops.snapshot_repo import get_snapshot_repo_manager
        repo_manager = get_snapshot_repo_manager()
        repo_manager.initialize()
        logger.info("Snapshot repository initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize snapshot repository: {e}")
        logger.warning("Snapshot repository operations may fail")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down Excel Diff Server")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=True,  # For development
    )
