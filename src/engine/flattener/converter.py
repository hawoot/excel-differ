"""
XLSB to XLSM converter using LibreOffice headless.
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import logging
import shutil

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Exception raised when XLSB conversion fails."""
    pass


def check_libreoffice_available() -> bool:
    """
    Check if LibreOffice is available at the configured path.

    Returns:
        True if LibreOffice is available, False otherwise
    """
    settings = get_settings()
    converter_path = Path(settings.CONVERTER_PATH)

    if not converter_path.exists():
        return False

    try:
        # Try to run LibreOffice with --version
        result = subprocess.run(
            [str(converter_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return False


def convert_xlsb_to_xlsm(xlsb_path: Path, output_dir: Optional[Path] = None) -> Path:
    """
    Convert XLSB file to XLSM using LibreOffice headless.

    Args:
        xlsb_path: Path to XLSB file
        output_dir: Optional output directory (defaults to temp directory)

    Returns:
        Path to converted XLSM file

    Raises:
        ConversionError: If conversion fails
    """
    settings = get_settings()
    converter_path = settings.CONVERTER_PATH

    if not check_libreoffice_available():
        raise ConversionError(
            f"LibreOffice not found at {converter_path}. "
            f"Please install LibreOffice or update CONVERTER_PATH in configuration."
        )

    if not xlsb_path.exists():
        raise ConversionError(f"Input file not found: {xlsb_path}")

    # Determine output directory
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="xlsb_convert_"))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Converting XLSB to XLSM: {xlsb_path}")

    try:
        # LibreOffice headless conversion command
        # --headless: run without GUI
        # --convert-to xlsm: output format
        # --outdir: output directory
        cmd = [
            str(converter_path),
            "--headless",
            "--convert-to", "xlsm",
            "--outdir", str(output_dir),
            str(xlsb_path)
        ]

        logger.debug(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.EXTRACTION_TIMEOUT_SECONDS
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise ConversionError(
                f"LibreOffice conversion failed with code {result.returncode}: {error_msg}"
            )

        # Find the converted file
        # LibreOffice creates output with same base name but .xlsm extension
        expected_output = output_dir / (xlsb_path.stem + ".xlsm")

        if not expected_output.exists():
            # Try to find any .xlsm file in output directory
            xlsm_files = list(output_dir.glob("*.xlsm"))
            if xlsm_files:
                expected_output = xlsm_files[0]
            else:
                raise ConversionError(
                    f"Conversion appeared to succeed but output file not found: {expected_output}"
                )

        logger.info(f"Successfully converted to: {expected_output}")
        return expected_output

    except subprocess.TimeoutExpired:
        raise ConversionError(
            f"Conversion timed out after {settings.EXTRACTION_TIMEOUT_SECONDS} seconds"
        )
    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError(f"Unexpected error during conversion: {e}")


def ensure_xlsm_format(file_path: Path, output_dir: Optional[Path] = None) -> Path:
    """
    Ensure file is in XLSM format, converting from XLSB if necessary.

    Args:
        file_path: Path to Excel file (XLSB or XLSM)
        output_dir: Optional output directory for conversion

    Returns:
        Path to XLSM file (original if already XLSM, converted if XLSB)

    Raises:
        ConversionError: If conversion is needed but fails
        ValueError: If file format is not supported
    """
    suffix = file_path.suffix.lower()

    if suffix == ".xlsm" or suffix == ".xlsx":
        # Already in a supported format
        logger.debug(f"File is already in {suffix} format: {file_path}")
        return file_path

    elif suffix == ".xlsb":
        # Need to convert
        logger.info(f"File is XLSB, conversion required: {file_path}")
        return convert_xlsb_to_xlsm(file_path, output_dir)

    elif suffix == ".xls":
        # Old Excel format - also needs conversion
        logger.info(f"File is XLS (legacy), conversion required: {file_path}")
        # LibreOffice can also convert XLS to XLSM
        # We'll reuse the same logic but with appropriate error message
        try:
            return convert_xlsb_to_xlsm(file_path, output_dir)  # Same function works for XLS
        except ConversionError as e:
            raise ConversionError(f"Failed to convert legacy XLS file: {e}")

    else:
        raise ValueError(
            f"Unsupported file format: {suffix}. "
            f"Supported formats: .xlsm, .xlsx, .xlsb, .xls"
        )


def get_libreoffice_version() -> Optional[str]:
    """
    Get LibreOffice version string.

    Returns:
        Version string or None if not available
    """
    settings = get_settings()
    converter_path = settings.CONVERTER_PATH

    try:
        result = subprocess.run(
            [str(converter_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Output is like: "LibreOffice 7.3.7.2 10(Build:2)"
            return result.stdout.strip()
    except:
        pass

    return None
