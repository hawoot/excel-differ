"""
NoOp Converter - Explicit no-conversion implementation
"""

from pathlib import Path
from typing import Optional

from components.core.interfaces import ConverterInterface, ConversionResult


class NoOpConverter(ConverterInterface):
    """
    Explicit no-operation converter.

    Use when you don't want any conversion (most common case).
    Makes intent clear: "I explicitly don't want conversion"
    """

    def __init__(self, config: dict):
        super().__init__(config)

    def needs_conversion(self, file_path: Path) -> bool:
        """Never needs conversion"""
        return False

    def can_convert(self, file_path: Path) -> bool:
        """Can "handle" anything by doing nothing"""
        return True

    def convert(
        self,
        input_path: Path,
        output_dir: Optional[Path] = None
    ) -> ConversionResult:
        """Return pass-through result"""
        return ConversionResult(
            success=True,
            input_path=input_path,
            output_path=None,
            conversion_performed=False,
            warnings=[],
            errors=[]
        )

    def get_name(self) -> str:
        return "NoOpConverter"
