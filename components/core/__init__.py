"""
Excel Differ - Core Interfaces and Data Classes

This module contains all abstract interfaces and data classes used across components.
"""

from .interfaces import (
    # Data classes
    SourceFileInfo,
    SourceSyncState,
    DownloadResult,
    UploadResult,
    ConversionResult,
    FlattenResult,
    ProcessingResult,
    WorkflowResult,

    # Interfaces
    SourceInterface,
    DestinationInterface,
    ConverterInterface,
    FlattenerInterface,
)

from .config import (
    RepoConfig,
    ComponentConfig,
    ExcelDifferConfig,
)

__all__ = [
    # Data classes
    'SourceFileInfo',
    'SourceSyncState',
    'DownloadResult',
    'UploadResult',
    'ConversionResult',
    'FlattenResult',
    'ProcessingResult',
    'WorkflowResult',

    # Interfaces
    'SourceInterface',
    'DestinationInterface',
    'ConverterInterface',
    'FlattenerInterface',

    # Config
    'RepoConfig',
    'ComponentConfig',
    'ExcelDifferConfig',
]
