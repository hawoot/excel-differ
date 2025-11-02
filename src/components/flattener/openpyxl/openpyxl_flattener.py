"""
OpenpyxlFlattener Plugin - FlattenerInterface implementation

This is the adapter/wrapper that makes the openpyxl Flattener conform
to the FlattenerInterface expected by the Excel Differ orchestrator.
"""

from pathlib import Path
from typing import Optional
import logging

from src.interfaces import FlattenerInterface, FlattenResult
from .flattener import Flattener

logger = logging.getLogger(__name__)


class OpenpyxlFlattener(FlattenerInterface):
    """
    Openpyxl-based flattener implementation.

    Wraps the openpyxl Flattener class to conform to FlattenerInterface.
    """

    def __init__(self, config: dict):
        """
        Initialise OpenpyxlFlattener with configuration.

        Args:
            config: Configuration dict with keys:
                - output_dir: Where to write flattened outputs (optional, default: ./tmp/flats)
                - include_computed: Extract computed values (optional, default: False)
                - include_literal: Extract literal values (optional, default: True)
                - include_formats: Extract cell formatting (optional, default: True)
                - include_origin_file: Include original Excel file in output (optional, default: False)
                - timeout: Maximum extraction time in seconds (optional, default: 900)
                - max_file_size_mb: Maximum file size in MB (optional, default: 200)
        """
        super().__init__(config)

        # Extract config with defaults
        output_dir = Path(config.get('output_dir', './tmp/flats'))
        include_computed = config.get('include_computed', False)
        include_literal = config.get('include_literal', True)
        include_formats = config.get('include_formats', True)
        include_origin_file = config.get('include_origin_file', False)
        timeout = config.get('timeout', 900)
        max_file_size_mb = config.get('max_file_size_mb', 200)

        # Create the underlying flattener
        self.flattener = Flattener(
            output_dir=output_dir,
            include_computed=include_computed,
            include_literal=include_literal,
            include_formats=include_formats,
            include_origin_file=include_origin_file,
            timeout=timeout,
            max_file_size_mb=max_file_size_mb
        )

        logger.info(f"OpenpyxlFlattener initialized with output_dir={output_dir}")

    def flatten(
        self,
        excel_file: Path,
        origin: Optional[str] = None,
    ) -> FlattenResult:
        """
        Flatten Excel file to text representation.

        Args:
            excel_file: Path to Excel file
            origin: Git repository URL (optional, for traceability)

        Returns:
            FlattenResult with success status and output paths
        """
        try:
            # Call the underlying flattener
            # Note: The underlying flattener's flatten() returns Path (flat_root)
            flat_root = self.flattener.flatten(
                excel_file=excel_file,
                origin=origin,
            )

            # Construct manifest path
            manifest_path = flat_root / 'manifest.json'

            return FlattenResult(
                success=True,
                input_path=excel_file,
                flat_root=flat_root,
                manifest_path=manifest_path if manifest_path.exists() else None,
                warnings=[],
                errors=[]
            )

        except Exception as e:
            logger.error(f"Flattening failed for {excel_file}: {e}", exc_info=True)
            return FlattenResult(
                success=False,
                input_path=excel_file,
                flat_root=None,
                manifest_path=None,
                warnings=[],
                errors=[str(e)]
            )

    def get_name(self) -> str:
        """Return name of this flattener implementation"""
        return "OpenpyxlFlattener"
