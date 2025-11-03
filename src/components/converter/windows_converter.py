"""
WindowsExcelConverter - Convert Excel files using Windows Excel COM

Converts .xlsb (binary) files to .xlsm (macro-enabled XML) format
using Windows COM automation.

Requires:
- Windows operating system
- Microsoft Excel installed
- pywin32 package (win32com.client, pythoncom, pywintypes)
"""

import logging
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from src.interfaces import ConverterInterface, ConversionResult

logger = logging.getLogger(__name__)


def _decode_com_error(hresult: int) -> str:
    """
    Decode Excel COM error codes to human-readable messages.

    Args:
        hresult: COM error code (HRESULT)

    Returns:
        Human-readable error message
    """
    errors = {
        -2146826072: "Object error (0x800a01a8) - Excel tried to update links/charts/events during automation",
        -2147024891: "Permission denied - file may be locked by another process",
        -2147024864: "File sharing violation - file is open elsewhere",
        -2147024894: "File not found",
        -2147483647: "Excel busy or crashed (RPC call rejected)",
        -2147352567: "Exception occurred in Excel",
    }
    return errors.get(hresult, f"COM error {hresult:#010x}")


def _kill_excel_processes():
    """
    Force-kill any hanging Excel processes.

    Uses taskkill on Windows to ensure Excel processes are terminated.
    """
    try:
        if platform.system() == 'Windows':
            subprocess.run(
                ['taskkill', '/F', '/IM', 'EXCEL.EXE'],
                capture_output=True,
                timeout=5
            )
            time.sleep(0.5)
    except Exception:
        pass  # Best effort - don't fail if taskkill fails


class WindowsExcelConverter(ConverterInterface):
    """
    Windows Excel COM-based converter.

    Uses COM automation to open Excel and perform SaveAs conversion.
    Only works on Windows with Excel installed.
    """

    def __init__(self, config: dict):
        """
        Initialize WindowsExcelConverter.

        Args:
            config: Configuration dict with:
                - timeout: Maximum conversion time in seconds (default: 300)

        Raises:
            RuntimeError: If not running on Windows
            ImportError: If win32com not available
        """
        super().__init__(config)
        self.timeout = config.get('timeout', 300)

        # Check platform
        if platform.system() != 'Windows':
            raise RuntimeError(
                "WindowsExcelConverter only works on Windows. "
                f"Current platform: {platform.system()}"
            )

        # Check if win32com is available
        try:
            import win32com.client
            self.win32com = win32com.client
        except ImportError:
            raise ImportError(
                "WindowsExcelConverter requires pywin32 package. "
                "Install with: pip install pywin32"
            )

    def needs_conversion(self, file_path: Path) -> bool:
        """
        Determine if file needs conversion.

        Returns True for .xlsb files (binary format).

        Args:
            file_path: Path to file to check

        Returns:
            True if file is .xlsb, False otherwise
        """
        return file_path.suffix.lower() == '.xlsb'

    def can_convert(self, file_path: Path) -> bool:
        """
        Check if this converter can handle the file.

        Returns True if:
        - Running on Windows
        - File is .xlsb
        - Excel is available

        Args:
            file_path: Path to file to convert

        Returns:
            True if conversion is possible, False otherwise
        """
        if platform.system() != 'Windows':
            return False

        if not self.needs_conversion(file_path):
            return False

        # Try to check if Excel is available (with retry)
        max_retries = 3
        for attempt in range(max_retries):
            excel = None
            try:
                import pythoncom
                pythoncom.CoInitialize()

                try:
                    # Use DispatchEx to create NEW Excel instance (not reuse existing)
                    excel = self.win32com.DispatchEx("Excel.Application")
                    excel.Quit()
                    excel = None

                    pythoncom.CoUninitialize()
                    return True

                except Exception as e:
                    logger.debug(f"Excel COM check attempt {attempt + 1}/{max_retries} failed: {e}")

                    # Cleanup
                    if excel is not None:
                        try:
                            excel.Quit()
                        except Exception:
                            pass

                    # Force cleanup
                    _kill_excel_processes()

                    pythoncom.CoUninitialize()

                    if attempt < max_retries - 1:
                        time.sleep(0.5)  # Wait before retry

            except Exception as e:
                logger.debug(f"Excel COM initialization attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)

        return False

    def convert(
        self,
        input_path: Path,
        output_dir: Optional[Path] = None
    ) -> ConversionResult:
        """
        Convert .xlsb file to .xlsm using Excel COM automation.

        Args:
            input_path: Path to .xlsb file
            output_dir: Output directory (default: same as input)

        Returns:
            ConversionResult with success status and output path
        """
        if not self.needs_conversion(input_path):
            # Not a .xlsb file, no conversion needed
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=None,
                conversion_performed=False,
                warnings=["File is not .xlsb, no conversion needed"],
                errors=[]
            )

        if not self.can_convert(input_path):
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=None,
                conversion_performed=False,
                warnings=[],
                errors=["Cannot convert: Excel not available or not on Windows"]
            )

        # Pre-checks
        if not input_path.exists():
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=None,
                conversion_performed=False,
                warnings=[],
                errors=[f"Input file not found: {input_path}"]
            )

        if not os.access(input_path, os.R_OK):
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=None,
                conversion_performed=False,
                warnings=[],
                errors=[f"Input file not readable: {input_path}"]
            )

        excel = None
        workbook = None

        try:
            # Initialize COM
            import pythoncom
            import pywintypes
            pythoncom.CoInitialize()

            try:
                # Determine output path
                if output_dir:
                    output_dir = Path(output_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = output_dir / (input_path.stem + '.xlsm')
                else:
                    output_path = input_path.parent / (input_path.stem + '.xlsm')

                # Start NEW Excel instance (DispatchEx creates isolated instance)
                # This ensures each conversion has its own Excel app - completely hermetic
                excel = self.win32com.DispatchEx("Excel.Application")

                # Non-critical: Try to set Visible to False
                try:
                    excel.Visible = False
                except:
                    pass  # Ignore errors - not critical

                # Non-critical: Set DisplayAlerts
                try:
                    excel.DisplayAlerts = False
                except:
                    pass  # Ignore errors - not critical

                # Non-critical: Disable events and updates
                try:
                    excel.EnableEvents = False  # Disable events to prevent automation issues
                    excel.AskToUpdateLinks = False  # Don't prompt for links
                    excel.ScreenUpdating = False
                except:
                    pass
                # Open workbook - minimal options
                abs_input = str(input_path.absolute())
                workbook = excel.Workbooks.Open(abs_input, UpdateLinks=0)

                # Convert: SaveAs with xlsm format
                # FileFormat 52 = xlOpenXMLWorkbookMacroEnabled (.xlsm)
                abs_output = str(output_path.absolute())
                workbook.SaveAs(abs_output, FileFormat=52)

                # Non-critical: Close workbook
                try:
                    workbook.Close(SaveChanges=False)
                except:
                    pass  # Ignore errors - not critical
                workbook = None

                # Non-critical: Quit Excel
                try:
                    excel.Quit()
                except:
                    pass  # Ignore errors - not critical
                excel = None

                logger.info(f"Successfully converted {input_path.name} to {output_path.name}")

                return ConversionResult(
                    success=True,
                    input_path=input_path,
                    output_path=output_path,
                    conversion_performed=True,
                    warnings=[],
                    errors=[]
                )

            except pywintypes.com_error as e:
                hresult = e.args[0] if e.args else 0
                error_msg = _decode_com_error(hresult)
                logger.error(
                    f"Excel COM conversion failed for {input_path.name}: {error_msg}",
                    exc_info=True
                )
                return ConversionResult(
                    success=False,
                    input_path=input_path,
                    output_path=None,
                    conversion_performed=False,
                    warnings=[],
                    errors=[f"Excel COM error: {error_msg}"]
                )

            except Exception as e:
                logger.error(
                    f"Excel conversion failed for {input_path.name}: {e}",
                    exc_info=True
                )
                return ConversionResult(
                    success=False,
                    input_path=input_path,
                    output_path=None,
                    conversion_performed=False,
                    warnings=[],
                    errors=[f"Conversion failed: {str(e)}"]
                )

            finally:
                # Non-critical cleanup: Ensure Excel is closed
                try:
                    if workbook is not None:
                        workbook.Close(SaveChanges=False)
                except:
                    pass  # Ignore errors - best effort cleanup

                try:
                    if excel is not None:
                        excel.Quit()
                except:
                    pass  # Ignore errors - best effort cleanup

                # Non-critical: Force cleanup - kill any hanging Excel processes
                try:
                    _kill_excel_processes()
                except:
                    pass  # Ignore errors - best effort cleanup

                # Non-critical: Uninitialize COM
                try:
                    pythoncom.CoUninitialize()
                except:
                    pass  # Ignore errors - best effort cleanup

        except Exception as e:
            # Catch any errors from COM initialization itself
            logger.error(f"COM initialization failed: {e}", exc_info=True)
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=None,
                conversion_performed=False,
                warnings=[],
                errors=[f"COM initialization failed: {str(e)}"]
            )

    def get_name(self) -> str:
        """Return name of this converter implementation"""
        return "WindowsExcelConverter"
