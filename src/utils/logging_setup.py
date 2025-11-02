"""
Shared logging setup for Excel Differ.

Provides colored console logging and detailed file logging for the entire application.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


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


def setup_logging(log_level: str = 'INFO', log_dir: Optional[str] = None, component: str = 'excel-differ'):
    """
    Set up logging for the application.

    Configures dual output:
    - Console: colored output at specified log level
    - File: detailed DEBUG output in log file

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (None = use default ./logs)
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
        log_path = Path('./logs')
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
