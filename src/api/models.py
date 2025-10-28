"""
Pydantic models for API request/response validation.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# Enums

class JobStatus(str, Enum):
    """Job status values."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class JobType(str, Enum):
    """Job type values."""
    EXTRACT = "extract"
    FLATTEN = "flatten"
    COMPARE = "compare"


class OutputFormat(str, Enum):
    """Output format for compare endpoint."""
    BOTH = "both"
    JSON = "json"
    TEXT = "text"


class ArchiveFormat(str, Enum):
    """Archive format for flatten endpoint."""
    ZIP = "zip"
    TAR_GZ = "tar.gz"


# Request Models

class ExtractRequest(BaseModel):
    """Request model for /extract endpoint (when using JSON)."""
    origin_repo: Optional[str] = Field(None, description="Origin repository URL")
    origin_path: Optional[str] = Field(None, description="Path in origin repository")
    origin_commit: Optional[str] = Field(None, description="Origin commit SHA")
    origin_commit_message: Optional[str] = Field(None, description="Origin commit message")
    file_url: Optional[str] = Field(None, description="URL to fetch file from")
    snapshot_repo_url: Optional[str] = Field(None, description="Override snapshot repo URL")
    include_evaluated: bool = Field(False, description="Include evaluated values")


class FlattenRequest(BaseModel):
    """Request model for /flatten endpoint (when using JSON)."""
    format: ArchiveFormat = Field(ArchiveFormat.ZIP, description="Archive format")
    include_evaluated: bool = Field(False, description="Include evaluated values")


class CompareRequest(BaseModel):
    """Request model for /compare endpoint (when using JSON)."""
    snapshot_path_a: Optional[str] = Field(None, description="Path to snapshot A in repo")
    snapshot_path_b: Optional[str] = Field(None, description="Path to snapshot B in repo")
    output: OutputFormat = Field(OutputFormat.BOTH, description="Output format")
    include_evaluated: bool = Field(False, description="Include evaluated values")
    diff_context: int = Field(3, ge=0, le=10, description="Context lines for unified diff")


# Response Models

class JobAcceptedResponse(BaseModel):
    """Response for accepted job."""
    status: str = "accepted"
    job_id: str = Field(..., description="Unique job identifier")


class ExtractResult(BaseModel):
    """Result for extract job."""
    commit_sha: str = Field(..., description="Commit SHA in snapshot repo")
    snapshot_path: str = Field(..., description="Path to snapshot in repo")
    manifest: Dict[str, Any] = Field(..., description="Manifest JSON")


class FlattenResult(BaseModel):
    """Result for flatten job."""
    archive_url: str = Field(..., description="URL to download archive")
    manifest: Dict[str, Any] = Field(..., description="Manifest JSON")
    size_bytes: int = Field(..., description="Archive size in bytes")


class CompareResult(BaseModel):
    """Result for compare job."""
    diff_json: List[Dict[str, Any]] = Field(..., description="Structured diff array")
    diff_unified: Optional[str] = Field(None, description="Unified diff text")
    summary: Dict[str, int] = Field(..., description="Summary statistics")


class JobStatusResponse(BaseModel):
    """Response for job status query."""
    job_id: str
    status: JobStatus
    type: JobType
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: int = Field(0, ge=0, le=100, description="Progress percentage")
    result: Optional[Dict[str, Any]] = Field(None, description="Job result (when success)")
    error: Optional[str] = Field(None, description="Error message (when failed)")


class HealthResponse(BaseModel):
    """Response for health check."""
    status: str = "ok"
    version: str
    queue_backend: str
    libreoffice_available: bool


class VersionResponse(BaseModel):
    """Response for version endpoint."""
    app_name: str
    app_version: str
    extractor_version: str
    libreoffice_version: Optional[str] = None


# Error Models

class ErrorResponse(BaseModel):
    """Generic error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
