"""
Workbook metadata extraction.

Extracts author, created/modified dates, Excel version, locale, etc.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from openpyxl.workbook import Workbook

from .normalizer import normalise_date_value

logger = logging.getLogger(__name__)


def extract_metadata(wb: Workbook) -> Dict[str, Any]:
    """
    Extract workbook-level metadata.

    Args:
        wb: Openpyxl workbook object

    Returns:
        Dictionary of metadata
    """
    logger.debug("Extracting workbook metadata...")

    metadata = {}

    try:
        # Core properties
        props = wb.properties

        if props:
            metadata['Author'] = props.creator or ''
            metadata['Last Modified By'] = props.lastModifiedBy or ''

            # Dates
            if props.created:
                metadata['Created'] = normalise_date_value(props.created)
            else:
                metadata['Created'] = ''

            if props.modified:
                metadata['Modified'] = normalise_date_value(props.modified)
            else:
                metadata['Modified'] = ''

            # Other properties
            metadata['Title'] = props.title or ''
            metadata['Subject'] = props.subject or ''
            metadata['Description'] = props.description or ''
            metadata['Keywords'] = props.keywords or ''
            metadata['Category'] = props.category or ''
            metadata['Company'] = getattr(props, 'company', '') or ''
            metadata['Version'] = getattr(props, 'version', '') or ''
        else:
            # No properties object
            logger.warning("Workbook has no properties object")
            metadata['Author'] = ''
            metadata['Last Modified By'] = ''
            metadata['Created'] = ''
            metadata['Modified'] = ''
            metadata['Title'] = ''
            metadata['Subject'] = ''
            metadata['Description'] = ''
            metadata['Keywords'] = ''
            metadata['Category'] = ''
            metadata['Company'] = ''
            metadata['Version'] = ''

        # Calculation properties
        calc_props = wb.calculation
        metadata['Calculation Mode'] = 'auto'  # Default
        if calc_props and hasattr(calc_props, 'calcMode'):
            metadata['Calculation Mode'] = calc_props.calcMode or 'auto'

        # Excel version (best effort)
        metadata['Excel Version'] = _get_excel_version(wb)

        # Locale (default assumption)
        metadata['Locale'] = 'en-US'

        logger.info(f"✓ Extracted metadata (author: {metadata['Author']}, "
                   f"sheets: {len(wb.worksheets)})")

    except Exception as e:
        logger.error(f"Error extracting metadata: {e}", exc_info=True)
        # Return partial metadata
        pass

    return metadata


def write_metadata_file(metadata: Dict[str, Any], output_path: Path) -> None:
    """
    Write metadata to a text file.

    Format: Key: Value (one per line)

    Args:
        metadata: Metadata dictionary
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# Workbook Metadata\n')
        f.write('# ==================\n\n')

        for key, value in metadata.items():
            f.write(f'{key}: {value}\n')

    logger.debug(f"Wrote metadata to: {output_path}")


def _get_excel_version(wb: Workbook) -> str:
    """
    Try to determine Excel version from workbook.

    Args:
        wb: Workbook object

    Returns:
        Version string or "unknown"
    """
    # Try to get from properties
    if wb.properties and hasattr(wb.properties, 'version'):
        version = wb.properties.version
        if version:
            return str(version)

    # Try to infer from file format (best effort)
    # This is difficult without access to the original file
    return 'unknown'
