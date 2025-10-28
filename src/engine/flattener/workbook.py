"""
Main workbook flattening orchestrator.
Coordinates all extraction modules to produce a complete flattened snapshot.
"""
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging
from openpyxl import load_workbook

from src.core.config import get_settings
from src.core.storage import get_file_hash, create_temp_dir
from src.engine.flattener.converter import ensure_xlsm_format
from src.engine.flattener.manifest import Manifest, create_snapshot_root_name
from src.engine.flattener.metadata import (
    extract_metadata,
    extract_structure_info,
    extract_defined_names,
    write_metadata_file,
    write_structure_file,
    write_defined_names_file,
)

logger = logging.getLogger(__name__)


class WorkbookFlattener:
    """
    Main class for flattening Excel workbooks into deterministic snapshots.
    """

    def __init__(self, include_evaluated: bool = False):
        """
        Initialize flattener.

        Args:
            include_evaluated: Whether to include evaluated cell values
        """
        self.settings = get_settings()
        self.include_evaluated = include_evaluated

    def flatten(
        self,
        input_file: Path,
        output_dir: Optional[Path] = None,
        origin_repo: Optional[str] = None,
        origin_path: Optional[str] = None,
        origin_commit: Optional[str] = None,
        origin_commit_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Flatten an Excel workbook to a deterministic snapshot.

        Args:
            input_file: Path to Excel file (XLSB, XLSM, or XLSX)
            output_dir: Optional output directory (defaults to temp)
            origin_repo: Optional origin repository URL
            origin_path: Optional origin file path
            origin_commit: Optional origin commit SHA
            origin_commit_message: Optional origin commit message

        Returns:
            Dictionary with:
                - snapshot_dir: Path to flattened snapshot directory
                - manifest: Manifest object
                - original_file: Path to original file (possibly converted)
                - warnings: List of warnings

        Raises:
            Exception: If flattening fails
        """
        logger.info(f"Starting flattening of: {input_file}")

        # Create output directory if not specified
        if output_dir is None:
            output_dir = create_temp_dir(prefix="flatten")

        try:
            # Step 1: Ensure file is in XLSM/XLSX format (convert XLSB if needed)
            working_file = ensure_xlsm_format(input_file, output_dir / "converted")
            logger.info(f"Working file: {working_file}")

            # Step 2: Calculate hash of original file
            original_hash = get_file_hash(input_file)
            logger.info(f"Original file hash: {original_hash}")

            # Step 3: Create snapshot root directory
            timestamp = datetime.now(timezone.utc)
            snapshot_root_name = create_snapshot_root_name(
                input_file.name, timestamp, original_hash
            )
            snapshot_dir = output_dir / snapshot_root_name
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Snapshot directory: {snapshot_dir}")

            # Step 4: Initialize manifest
            manifest = Manifest(
                workbook_filename=input_file.name,
                original_sha256=original_hash,
                include_evaluated=self.include_evaluated,
            )

            # Set origin information
            manifest.set_origin(
                origin_repo=origin_repo,
                origin_path=origin_path,
                origin_commit=origin_commit,
                origin_commit_message=origin_commit_message,
            )

            # Step 5: Copy original file to snapshot
            original_dir = snapshot_dir / "original"
            original_dir.mkdir(parents=True, exist_ok=True)
            original_copy = original_dir / input_file.name
            shutil.copy2(input_file, original_copy)
            logger.info(f"Copied original file to: {original_copy}")

            # Step 6: Load workbook
            logger.info("Loading workbook...")
            wb = load_workbook(working_file, data_only=False, keep_vba=True)

            # Step 7: Extract workbook-level information
            logger.info("Extracting workbook metadata...")
            self._extract_workbook_level(wb, snapshot_dir, manifest)

            # Step 8: Extract sheet-level information
            logger.info("Extracting sheet data...")
            self._extract_sheets(wb, snapshot_dir, manifest)

            # Step 9: Extract VBA (if present)
            logger.info("Extracting VBA...")
            self._extract_vba(working_file, snapshot_dir, manifest)

            # Step 10: Extract tables, charts, pivots
            logger.info("Extracting tables, charts, and pivots...")
            self._extract_tables_charts_pivots(wb, snapshot_dir, manifest)

            # Step 11: Extract styles
            logger.info("Extracting styles...")
            self._extract_styles(wb, snapshot_dir, manifest)

            # Step 12: Create extraction log
            self._create_extraction_log(snapshot_dir, manifest)

            # Step 13: Add all files to manifest
            logger.info("Building file inventory...")
            self._add_all_files_to_manifest(snapshot_dir, manifest)

            # Step 14: Save manifest
            manifest_path = snapshot_dir / "manifest.json"
            manifest.save(manifest_path)

            logger.info(f"Flattening complete: {snapshot_dir}")

            return {
                "snapshot_dir": snapshot_dir,
                "manifest": manifest,
                "original_file": input_file,
                "warnings": manifest.warnings,
            }

        except Exception as e:
            logger.exception(f"Failed to flatten workbook: {e}")
            raise

    def _extract_workbook_level(
        self, wb, snapshot_dir: Path, manifest: Manifest
    ) -> None:
        """Extract workbook-level information (metadata, structure, defined names, etc.)."""
        workbook_dir = snapshot_dir / "workbook"
        workbook_dir.mkdir(parents=True, exist_ok=True)

        # Metadata
        metadata = extract_metadata(wb)
        write_metadata_file(metadata, workbook_dir / "metadata.txt")

        # Structure
        structure = extract_structure_info(wb)
        write_structure_file(structure, workbook_dir / "structure.txt")

        # Add sheets to manifest
        for sheet_info in structure["sheets"]:
            manifest.add_sheet(**sheet_info)

        # Defined names
        defined_names = extract_defined_names(wb)
        write_defined_names_file(defined_names, workbook_dir / "defined_names.txt")

        # Calculation chain, external links, connections, add-ins
        # These will be implemented in separate modules
        # For now, create empty placeholder files
        (workbook_dir / "calculation_chain.txt").write_text("# Calculation chain (not yet implemented)\n")
        (workbook_dir / "external_links.txt").write_text("# External links (not yet implemented)\n")
        (workbook_dir / "connections.txt").write_text("# Connections (not yet implemented)\n")
        (workbook_dir / "addins.txt").write_text("# Add-ins (not yet implemented)\n")

    def _extract_sheets(self, wb, snapshot_dir: Path, manifest: Manifest) -> None:
        """Extract all sheet-level data (formulas, values, formats, etc.)."""
        sheets_dir = snapshot_dir / "sheets"
        sheets_dir.mkdir(parents=True, exist_ok=True)

        # Import sheet extraction modules (to be implemented)
        try:
            from src.engine.flattener.sheets import extract_sheet_data
        except ImportError:
            logger.warning("Sheet extraction module not yet implemented")
            # Create placeholder
            for idx, sheet in enumerate(wb.worksheets, start=1):
                from src.engine.flattener.normalizer import normalize_sheet_name
                safe_name = normalize_sheet_name(sheet.title)
                prefix = f"{idx:02d}.{safe_name}"

                # Create placeholder files
                (sheets_dir / f"{prefix}.formulas.txt").write_text("# Formulas (not yet implemented)\n")
                (sheets_dir / f"{prefix}.values_hardcoded.txt").write_text("# Values (not yet implemented)\n")
                (sheets_dir / f"{prefix}.cell_formats.txt").write_text("# Formats (not yet implemented)\n")
            return

        # Extract each sheet
        for idx, sheet in enumerate(wb.worksheets, start=1):
            logger.info(f"Extracting sheet {idx}/{len(wb.worksheets)}: {sheet.title}")
            extract_sheet_data(
                sheet, idx, sheets_dir, self.include_evaluated, manifest
            )

    def _extract_vba(self, workbook_path: Path, snapshot_dir: Path, manifest: Manifest) -> None:
        """Extract VBA modules."""
        vba_dir = snapshot_dir / "vba"
        vba_dir.mkdir(parents=True, exist_ok=True)

        # Import VBA extraction module (to be implemented)
        try:
            from src.engine.flattener.vba import extract_vba_modules
            extract_vba_modules(workbook_path, vba_dir, manifest)
        except ImportError:
            logger.warning("VBA extraction module not yet implemented")
            (vba_dir / "vba_extraction_pending.txt").write_text("# VBA extraction not yet implemented\n")

    def _extract_tables_charts_pivots(self, wb, snapshot_dir: Path, manifest: Manifest) -> None:
        """Extract tables, charts, and pivot tables."""
        # Create directories
        (snapshot_dir / "tables").mkdir(parents=True, exist_ok=True)
        (snapshot_dir / "charts").mkdir(parents=True, exist_ok=True)
        (snapshot_dir / "pivots").mkdir(parents=True, exist_ok=True)

        # Placeholder for now
        (snapshot_dir / "tables" / "tables_pending.txt").write_text("# Tables extraction not yet implemented\n")
        (snapshot_dir / "charts" / "charts_pending.txt").write_text("# Charts extraction not yet implemented\n")
        (snapshot_dir / "pivots" / "pivots_pending.txt").write_text("# Pivots extraction not yet implemented\n")

    def _extract_styles(self, wb, snapshot_dir: Path, manifest: Manifest) -> None:
        """Extract styles, number formats, and theme."""
        styles_dir = snapshot_dir / "styles"
        styles_dir.mkdir(parents=True, exist_ok=True)

        # Placeholder for now
        (styles_dir / "cell_styles.txt").write_text("# Cell styles (not yet implemented)\n")
        (styles_dir / "number_formats.txt").write_text("# Number formats (not yet implemented)\n")
        (styles_dir / "theme.txt").write_text("# Theme (not yet implemented)\n")

    def _create_extraction_log(self, snapshot_dir: Path, manifest: Manifest) -> None:
        """Create extraction log with warnings and info."""
        logs_dir = snapshot_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_path = logs_dir / "extraction.log"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("Extraction Log\n")
            f.write("==============\n\n")
            f.write(f"Extracted at: {manifest.extracted_at}\n")
            f.write(f"Extractor version: {manifest.extractor_version}\n")
            f.write(f"Include evaluated: {manifest.include_evaluated}\n\n")

            if manifest.warnings:
                f.write("Warnings:\n")
                for warning in manifest.warnings:
                    f.write(f"  - {warning}\n")
            else:
                f.write("No warnings.\n")

    def _add_all_files_to_manifest(self, snapshot_dir: Path, manifest: Manifest) -> None:
        """Add all generated files to the manifest with their hashes."""
        for file_path in snapshot_dir.rglob("*"):
            if file_path.is_file() and file_path.name != "manifest.json":
                manifest.add_file(file_path, snapshot_dir)
