"""
WindowsExcelConverter - Convert Excel files using Windows Excel COM

Converts .xlsb (binary) files to .xlsm (macro-enabled XML) format
using Windows COM automation.

Requires:
- Windows operating system
- Microsoft Excel installed
- pywin32 package (win32com.client)
"""

import platform
import time
from pathlib import Path
from typing import Optional

from src.interfaces import ConverterInterface, ConversionResult


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

        # Try to check if Excel is available
        try:
            excel = self.win32com.Dispatch("Excel.Application")
            excel.Quit()
            return True
        except:
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

        excel = None
        workbook = None

        try:
            # Determine output path
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / (input_path.stem + '.xlsm')
            else:
                output_path = input_path.parent / (input_path.stem + '.xlsm')

            # Start Excel
            excel = self.win32com.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False

            # Open workbook
            abs_input = str(input_path.absolute())
            workbook = excel.Workbooks.Open(abs_input)

            # Convert: SaveAs with xlsm format
            # FileFormat 52 = xlOpenXMLWorkbookMacroEnabled (.xlsm)
            abs_output = str(output_path.absolute())
            workbook.SaveAs(abs_output, FileFormat=52)

            # Close workbook
            workbook.Close(SaveChanges=False)
            workbook = None

            # Quit Excel
            excel.Quit()
            excel = None

            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                conversion_performed=True,
                warnings=[],
                errors=[]
            )

        except Exception as e:
            error_msg = f"Excel COM conversion failed: {str(e)}"

            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=None,
                conversion_performed=False,
                warnings=[],
                errors=[error_msg]
            )

        finally:
            # Cleanup: ensure Excel is closed
            try:
                if workbook is not None:
                    workbook.Close(SaveChanges=False)
            except:
                pass

            try:
                if excel is not None:
                    excel.Quit()
            except:
                pass

    def get_name(self) -> str:
        """Return name of this converter implementation"""
        return "WindowsExcelConverter"
