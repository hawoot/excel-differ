"""
Workbook structure extraction.

Extracts sheet order, visibility, tab colours, and other structural information.
"""
import logging
from pathlib import Path
from typing import Dict, Any, List

from openpyxl.workbook import Workbook

logger = logging.getLogger(__name__)


def extract_structure(wb: Workbook) -> List[Dict[str, Any]]:
    """
    Extract workbook structure information.

    Args:
        wb: Openpyxl workbook object

    Returns:
        List of sheet structure dictionaries
    """
    logger.debug("Extracting workbook structure...")

    structure = []

    for index, ws in enumerate(wb.worksheets, start=1):
        sheet_info = {
            'index': index,
            'name': ws.title,
            'sheetId': ws.sheet_id if hasattr(ws, 'sheet_id') else index,
            'visible': ws.sheet_state == 'visible',
            'state': ws.sheet_state,  # visible, hidden, veryHidden
            'tab_color': _get_tab_color(ws),
            'row_count': ws.max_row,
            'column_count': ws.max_column,
        }

        structure.append(sheet_info)
        logger.debug(f"Extracted structure for sheet: {ws.title} (index={index})")

    logger.info(f"✓ Extracted structure for {len(structure)} sheets")

    return structure


def write_structure_file(structure: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write structure information to a text file.

    Format:
    Sheet: <name>
      Index: <index>
      Sheet ID: <sheetId>
      Visible: <true/false>
      State: <visible/hidden/veryHidden>
      Tab Colour: <colour or none>
      Rows: <count>
      Columns: <count>

    Args:
        structure: List of sheet structure dictionaries
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# Workbook Structure\n')
        f.write('# ' + '=' * 50 + '\n\n')

        for sheet in structure:
            f.write(f"Sheet: {sheet['name']}\n")
            f.write(f"  Index: {sheet['index']}\n")
            f.write(f"  Sheet ID: {sheet['sheetId']}\n")
            f.write(f"  Visible: {str(sheet['visible']).lower()}\n")
            f.write(f"  State: {sheet['state']}\n")
            f.write(f"  Tab Colour: {sheet['tab_color']}\n")
            f.write(f"  Rows: {sheet['row_count']}\n")
            f.write(f"  Columns: {sheet['column_count']}\n")
            f.write('\n')

    logger.debug(f"Wrote structure to: {output_path}")


def _get_tab_color(ws) -> str:
    """
    Get tab colour for a worksheet.

    Args:
        ws: Worksheet object

    Returns:
        Colour string (RGB hex) or 'none'
    """
    try:
        if hasattr(ws, 'sheet_properties') and ws.sheet_properties:
            tab_color = ws.sheet_properties.tabColor
            if tab_color:
                # Try to get RGB value
                if hasattr(tab_color, 'rgb') and tab_color.rgb:
                    return tab_color.rgb
                elif hasattr(tab_color, 'theme') and tab_color.theme is not None:
                    return f'theme:{tab_color.theme}'
                elif hasattr(tab_color, 'indexed') and tab_color.indexed is not None:
                    return f'indexed:{tab_color.indexed}'
    except Exception as e:
        logger.warning(f"Error extracting tab colour: {e}")

    return 'none'
