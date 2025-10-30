"""
Utility functions for the Excel Flattener.

Provides file hashing, path handling, logging setup, and configuration loading.
"""
import hashlib
import logging
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


# ============================================================================
# Configuration Loading
# ============================================================================

def load_config():
    """
    Load configuration from environment variables.

    Looks for .env file in current directory and parents.
    Returns a dict with all FLATTENER_* settings.
    """
    # Load .env file if it exists
    load_dotenv()

    config = {
        'output_dir': Path(os.getenv('FLATTENER_OUTPUT_DIR', './tmp/flats')),
        'log_dir': os.getenv('FLATTENER_LOG_DIR', './tmp/logs'),
        'log_level': os.getenv('FLATTENER_LOG_LEVEL', 'INFO').upper(),
        'extraction_timeout': int(os.getenv('FLATTENER_EXTRACTION_TIMEOUT', '900')),
        'max_file_size_mb': int(os.getenv('FLATTENER_MAX_FILE_SIZE_MB', '200')),
        'temp_dir': os.getenv('FLATTENER_TEMP_DIR', './tmp/temp'),
    }

    return config


# ============================================================================
# Logging Setup
# ============================================================================

class ColourFormatter(logging.Formatter):
    """
    Custom formatter with colour support for console output.
    """

    # ANSI colour codes
    COLOURS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m',     # Reset
    }

    def format(self, record):
        """Format log record with colour for console."""
        # Add colour to level name
        levelname = record.levelname
        if levelname in self.COLOURS:
            record.levelname = f"{self.COLOURS[levelname]}{levelname:<8}{self.COLOURS['RESET']}"

        return super().format(record)


def setup_logging(log_level: str = 'INFO', log_dir: Optional[str] = None, component: str = 'flattener'):
    """
    Set up logging for the flattener.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (None = use default ./tmp/logs)
        component: Component name for log filename

    Returns:
        Logger instance
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))

    # Remove existing handlers
    logger.handlers = []

    # Console handler (with colour)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_formatter = ColourFormatter(
        '[%(asctime)s] %(levelname)s | %(name)-12s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (no colour)
    if log_dir is None:
        log_path = Path('./tmp/logs')
    else:
        log_path = Path(log_dir)

    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_path / f'{component}_{timestamp}.log'

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Always DEBUG in file
    file_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s | %(name)-12s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logger.info(f"Logging initialised (level: {log_level}, file: {log_file})")

    return logger


# ============================================================================
# File Operations
# ============================================================================

def get_file_hash(file_path: Path, algorithm: str = 'sha256') -> str:
    """
    Calculate hash of a file.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hex string of file hash
    """
    hash_obj = hashlib.new(algorithm)

    with open(file_path, 'rb') as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b''):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def sanitise_filename(name: str, replacement: str = '_') -> str:
    """
    Sanitise a string for use as a filename.

    Replaces invalid filename characters with replacement character.

    Args:
        name: String to sanitise
        replacement: Character to replace invalid chars with

    Returns:
        Sanitised filename string
    """
    if not name:
        return 'unnamed'

    # Replace invalid characters (Windows + Unix)
    # Invalid: / \ : * ? " < > |
    invalid_chars = r'[/\\:*?"<>|]'
    name = re.sub(invalid_chars, replacement, name)

    # Collapse multiple replacements
    name = re.sub(f'{re.escape(replacement)}+', replacement, name)

    # Remove leading/trailing replacements
    name = name.strip(replacement)

    # Handle empty result
    if not name:
        return 'unnamed'

    return name


def create_temp_dir(prefix: str = 'flattener_', temp_dir: str = '') -> Path:
    """
    Create a temporary directory.

    Args:
        prefix: Prefix for directory name
        temp_dir: Base temp directory (empty = system temp)

    Returns:
        Path to created temp directory
    """
    if temp_dir:
        base_dir = Path(temp_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        temp_path = base_dir / f'{prefix}{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_path
    else:
        # Use system temp
        return Path(tempfile.mkdtemp(prefix=prefix))


def create_flat_root_name(filename: str, timestamp: datetime, file_hash: str) -> str:
    """
    Create a flat root directory name.

    Format: <filename>-flat-<ISO8601>-<hash>
    Example: budget-flat-20251027T143022Z-a3f5c8d1

    Args:
        filename: Original filename (without extension)
        timestamp: Timestamp of extraction (datetime object)
        file_hash: SHA256 hash of original file (hex string)

    Returns:
        Flat root directory name
    """
    # Remove extension from filename
    name = Path(filename).stem

    # Sanitise filename
    name = sanitise_filename(name)

    # Format timestamp as ISO8601 compact
    ts_str = timestamp.strftime('%Y%m%dT%H%M%SZ')

    # Take first 8 chars of hash
    hash_short = file_hash[:8]

    return f"{name}-flat-{ts_str}-{hash_short}"


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to directory

    Returns:
        Path to directory (same as input)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_file_size(file_path: Path, max_size_mb: int) -> None:
    """
    Validate that a file is not too large.

    Args:
        file_path: Path to file to check
        max_size_mb: Maximum file size in megabytes

    Raises:
        ValueError: If file is too large
    """
    file_size = file_path.stat().st_size
    file_size_mb = file_size / (1024 * 1024)

    if file_size_mb > max_size_mb:
        raise ValueError(
            f"File too large: {file_size_mb:.1f} MB "
            f"(maximum: {max_size_mb} MB)"
        )


# ============================================================================
# Cell Address Utilities
# ============================================================================

def sort_key_for_cell_address(address: str) -> tuple:
    """
    Generate a sort key for cell addresses (row-major order).

    Args:
        address: Cell address (e.g., A1, B2, AA100)

    Returns:
        Tuple (row, column) for sorting
    """
    # Remove sheet name if present
    if '!' in address:
        address = address.split('!')[-1]

    # Remove dollar signs (absolute references)
    address = address.replace('$', '')

    # Parse column letters and row number
    match = re.match(r'^([A-Z]+)(\d+)$', address.upper())
    if not match:
        return (0, 0)

    col_letters, row_num = match.groups()

    # Convert column letters to number (A=1, B=2, ..., Z=26, AA=27, etc.)
    col_num = 0
    for char in col_letters:
        col_num = col_num * 26 + (ord(char) - ord('A') + 1)

    return (int(row_num), col_num)


def normalise_cell_address(address: str) -> str:
    """
    Normalise a cell address to uppercase without dollar signs.

    Used for sorting and comparison.

    Args:
        address: Cell address (e.g., a1, $A$1, Sheet1!B2)

    Returns:
        Normalised address (e.g., A1, A1, SHEET1!B2)
    """
    if not address:
        return ''

    # Uppercase
    address = address.upper()

    # Remove dollar signs
    address = address.replace('$', '')

    return address
