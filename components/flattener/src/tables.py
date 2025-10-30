"""
Excel table (ListObject) extraction.

Extracts structured table definitions, including columns, filters, and styles.
"""
import logging
from pathlib import Path
from typing import Dict, Any, List

from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)


def extract_tables(wb: Workbook) -> List[Dict[str, Any]]:
    """
    Extract all tables from workbook.

    Args:
        wb: Openpyxl workbook object

    Returns:
        List of table dictionaries
    """
    logger.debug("Extracting tables from workbook...")

    tables = []

    for ws in wb.worksheets:
        sheet_tables = _extract_sheet_tables(ws)
        tables.extend(sheet_tables)

    logger.info(f"✓ Extracted {len(tables)} tables")
    return tables


def _extract_sheet_tables(ws: Worksheet) -> List[Dict[str, Any]]:
    """
    Extract tables from a single worksheet.

    Args:
        ws: Worksheet object

    Returns:
        List of table dictionaries
    """
    tables = []

    if not hasattr(ws, 'tables') or not ws.tables:
        return tables

    for table_name, table in ws.tables.items():
        try:
            table_info = {
                'sheet': ws.title,
                'name': table_name,
                'display_name': table.displayName if hasattr(table, 'displayName') else table_name,
                'ref': str(table.ref) if table.ref else '',
                'table_style': table.tableStyleInfo.name if hasattr(table, 'tableStyleInfo') and table.tableStyleInfo else None,
                'show_header_row': True,  # Default
                'show_totals_row': False,  # Default
                'columns': []
            }

            # Get header row setting
            if hasattr(table, 'headerRowCount'):
                table_info['show_header_row'] = table.headerRowCount > 0

            # Get totals row setting
            if hasattr(table, 'totalsRowCount'):
                table_info['show_totals_row'] = table.totalsRowCount > 0

            # Extract columns
            if hasattr(table, 'tableColumns') and table.tableColumns:
                for col in table.tableColumns:
                    col_info = {
                        'id': col.id,
                        'name': col.name,
                    }

                    # Get totals row function if present
                    if hasattr(col, 'totalsRowFunction') and col.totalsRowFunction:
                        col_info['totals_function'] = col.totalsRowFunction

                    table_info['columns'].append(col_info)

            tables.append(table_info)
            logger.debug(f"Extracted table: {table_name} from {ws.title}")

        except Exception as e:
            logger.warning(f"Error extracting table {table_name}: {e}")

    return tables


def write_tables_file(tables: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write tables information to text file.

    Format:
    Table: TableName
      Sheet: Sheet1
      Display Name: My Table
      Range: A1:E10
      Style: TableStyleMedium2
      Header Row: true
      Totals Row: false
      Columns:
        - ID: 1, Name: Column1
        - ID: 2, Name: Column2, Totals: sum

    Args:
        tables: List of table dictionaries
        output_path: Path to output file
    """
    if not tables:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# Excel Tables\n')
        f.write('# =============\n\n')

        for table in tables:
            f.write(f"Table: {table['name']}\n")
            f.write(f"  Sheet: {table['sheet']}\n")
            f.write(f"  Display Name: {table['display_name']}\n")
            f.write(f"  Range: {table['ref']}\n")

            if table['table_style']:
                f.write(f"  Style: {table['table_style']}\n")

            f.write(f"  Header Row: {str(table['show_header_row']).lower()}\n")
            f.write(f"  Totals Row: {str(table['show_totals_row']).lower()}\n")

            if table['columns']:
                f.write('  Columns:\n')
                for col in table['columns']:
                    col_str = f"    - ID: {col['id']}, Name: {col['name']}"
                    if 'totals_function' in col:
                        col_str += f", Totals: {col['totals_function']}"
                    f.write(col_str + '\n')

            f.write('\n')

    logger.debug(f"Wrote tables to: {output_path}")


def extract_autofilters(wb: Workbook) -> List[Dict[str, Any]]:
    """
    Extract autofilter definitions from workbook.

    Args:
        wb: Openpyxl workbook object

    Returns:
        List of autofilter dictionaries
    """
    logger.debug("Extracting autofilters from workbook...")

    autofilters = []

    for ws in wb.worksheets:
        if hasattr(ws, 'auto_filter') and ws.auto_filter:
            try:
                filter_info = {
                    'sheet': ws.title,
                    'ref': ws.auto_filter.ref if ws.auto_filter.ref else None,
                }

                if filter_info['ref']:
                    autofilters.append(filter_info)
                    logger.debug(f"Extracted autofilter from {ws.title}: {filter_info['ref']}")

            except Exception as e:
                logger.warning(f"Error extracting autofilter from {ws.title}: {e}")

    logger.info(f"✓ Extracted {len(autofilters)} autofilters")
    return autofilters


def write_autofilters_file(autofilters: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write autofilter information to text file.

    Format:
    Sheet: Sheet1
      Range: A1:E10

    Args:
        autofilters: List of autofilter dictionaries
        output_path: Path to output file
    """
    if not autofilters:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# AutoFilters\n')
        f.write('# ============\n\n')

        for filter_info in autofilters:
            f.write(f"Sheet: {filter_info['sheet']}\n")
            f.write(f"  Range: {filter_info['ref']}\n")
            f.write('\n')

    logger.debug(f"Wrote autofilters to: {output_path}")
