"""
Excel Flattener - Convert Excel workbooks to diff-friendly text.

Main exports:
- Flattener: Main flattener class
- load_config: Load configuration from environment
- setup_logging: Setup logging configuration
"""
from .flattener import Flattener, TimeoutError
from .utils import load_config, setup_logging

__version__ = '2.1.0'

__all__ = [
    'Flattener',
    'TimeoutError',
    'load_config',
    'setup_logging',
]
