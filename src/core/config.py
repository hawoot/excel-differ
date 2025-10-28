"""
Configuration module for Excel Diff Server.
All settings are loaded from environment variables.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server Settings
    HOST: str = Field(default="0.0.0.0", description="API server host")
    PORT: int = Field(default=8000, description="API server port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Snapshot Repository (Repo B) Settings
    SNAPSHOT_REPO_URL: str = Field(
        default="",
        description="Default Snapshot Repo (Repo B) URL (git@github.com:org/repo.git or https://...)"
    )
    SNAPSHOT_REPO_LOCAL_PATH: Path = Field(
        default=Path("/tmp/snapshot-repo"),
        description="Local checked-out mirror path for Repo B"
    )

    # Git Authentication
    # For SSH: ensure SSH keys are configured in ~/.ssh/
    # For HTTPS: include token in SNAPSHOT_REPO_URL like https://token@github.com/org/repo.git
    GIT_USER_NAME: str = Field(default="Excel Diff Server", description="Git commit author name")
    GIT_USER_EMAIL: str = Field(default="excel-diff@example.com", description="Git commit author email")

    # LibreOffice Converter
    CONVERTER_PATH: str = Field(
        default="/usr/bin/libreoffice",
        description="Path to LibreOffice binary for XLSB conversion"
    )

    # Upload & Processing Limits
    MAX_UPLOAD_BYTES: int = Field(
        default=200 * 1024 * 1024,  # 200 MB
        description="Maximum upload file size in bytes"
    )
    EXTRACTION_TIMEOUT_SECONDS: int = Field(
        default=900,  # 15 minutes
        description="Timeout for extraction jobs"
    )

    # Job & Result Storage
    RESULT_TTL_SECONDS: int = Field(
        default=36000,  # 10 hours
        description="Time to live for job results"
    )
    TEMP_STORAGE_PATH: Path = Field(
        default=Path("/tmp/excel-differ"),
        description="Path for temporary job artifacts"
    )

    # Job Queue Configuration
    QUEUE_BACKEND: str = Field(
        default="celery",
        description="Job queue backend: 'celery' or 'multiprocessing'"
    )

    # Celery Settings (only used if QUEUE_BACKEND == "celery")
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL (Redis)"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL (Redis)"
    )
    WORKER_CONCURRENCY: int = Field(
        default=4,
        description="Number of concurrent worker processes"
    )

    # Extraction Options
    INCLUDE_EVALUATED_DEFAULT: bool = Field(
        default=False,
        description="Default value for include_evaluated option"
    )

    # Callback/Webhook Settings (optional enhancement)
    CALLBACKS_ENABLED: bool = Field(
        default=False,
        description="Enable callback/webhook support (future enhancement)"
    )

    # Application Metadata
    APP_NAME: str = "Excel Diff Server"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    @validator("QUEUE_BACKEND")
    def validate_queue_backend(cls, v):
        """Ensure queue backend is valid."""
        if v not in ["celery", "multiprocessing"]:
            raise ValueError("QUEUE_BACKEND must be 'celery' or 'multiprocessing'")
        return v

    @validator("TEMP_STORAGE_PATH", "SNAPSHOT_REPO_LOCAL_PATH")
    def ensure_path_exists(cls, v):
        """Create directories if they don't exist."""
        if isinstance(v, (str, Path)):
            path = Path(v)
            path.mkdir(parents=True, exist_ok=True)
            return path
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
