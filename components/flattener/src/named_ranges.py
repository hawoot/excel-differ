"""
Named ranges extraction from Excel workbooks.

Extracts both workbook-level and worksheet-level named ranges.
"""
import logging
from pathlib import Path
from typing import Dict, Any, List

from openpyxl.workbook import Workbook

logger = logging.getLogger(__name__)


def extract_named_ranges(wb: Workbook) -> List[Dict[str, Any]]:
    """
    Extract all named ranges from workbook.

    Includes:
    - Workbook-level named ranges
    - Worksheet-level named ranges

    Args:
        wb: Openpyxl workbook object

    Returns:
        List of named range dictionaries
    """
    logger.debug("Extracting named ranges from workbook...")

    named_ranges = []

    # Workbook-level named ranges
    if hasattr(wb, 'defined_names') and wb.defined_names:
        for name, defn in wb.defined_names.items():
            try:
                range_info = {
                    'name': name,
                    'scope': 'workbook',
                    'scope_sheet': None,
                    'value': str(defn.value) if defn.value else '',
                    'type': _get_range_type(defn)
                }

                # Check if scoped to specific sheet
                if hasattr(defn, 'localSheetId') and defn.localSheetId is not None:
                    try:
                        sheet = wb.worksheets[defn.localSheetId]
                        range_info['scope'] = 'worksheet'
                        range_info['scope_sheet'] = sheet.title
                    except (IndexError, AttributeError):
                        pass

                named_ranges.append(range_info)
                logger.debug(f"Extracted named range: {name} ({range_info['scope']})")

            except Exception as e:
                logger.warning(f"Error extracting named range {name}: {e}")

    # Sort by name for determinism
    named_ranges.sort(key=lambda x: x['name'])

    logger.info(f"✓ Extracted {len(named_ranges)} named ranges")
    return named_ranges


def _get_range_type(defn) -> str:
    """
    Determine the type of named range.

    Args:
        defn: DefinedName object

    Returns:
        Type string: range, constant, formula
    """
    if not defn.value:
        return 'unknown'

    value = str(defn.value)

    # Check if it's a cell reference
    if '!' in value or ':' in value or value.startswith('$'):
        return 'range'

    # Check if it's a formula
    if value.startswith('='):
        return 'formula'

    # Otherwise it's a constant
    return 'constant'


def write_named_ranges_file(named_ranges: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write named ranges to text file.

    Format:
    Name: SalesData
      Scope: workbook
      Type: range
      Value: Sheet1!$A$1:$E$100

    Name: TaxRate
      Scope: worksheet
      Sheet: Calculations
      Type: constant
      Value: 0.20

    Args:
        named_ranges: List of named range dictionaries
        output_path: Path to output file
    """
    if not named_ranges:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# Named Ranges\n')
        f.write('# =============\n\n')

        for nr in named_ranges:
            f.write(f"Name: {nr['name']}\n")
            f.write(f"  Scope: {nr['scope']}\n")

            if nr['scope_sheet']:
                f.write(f"  Sheet: {nr['scope_sheet']}\n")

            f.write(f"  Type: {nr['type']}\n")
            f.write(f"  Value: {nr['value']}\n")
            f.write('\n')

    logger.debug(f"Wrote named ranges to: {output_path}")
