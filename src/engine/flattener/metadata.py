"""
Workbook metadata extraction.
Extracts author, created/modified dates, Excel version, locale, etc.
"""
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from openpyxl import load_workbook
from openpyxl.workbook import Workbook

logger = logging.getLogger(__name__)


def extract_metadata(wb: Workbook) -> Dict[str, Any]:
    """
    Extract workbook-level metadata.

    Args:
        wb: Openpyxl workbook object

    Returns:
        Dictionary of metadata
    """
    metadata = {}

    try:
        # Core properties
        props = wb.properties

        if props:
            metadata["author"] = props.creator or ""
            metadata["last_modified_by"] = props.lastModifiedBy or ""

            # Dates
            if props.created:
                metadata["created"] = _format_datetime(props.created)
            if props.modified:
                metadata["modified"] = _format_datetime(props.modified)

            # Other properties
            metadata["title"] = props.title or ""
            metadata["subject"] = props.subject or ""
            metadata["description"] = props.description or ""
            metadata["keywords"] = props.keywords or ""
            metadata["category"] = props.category or ""
            metadata["company"] = props.company or ""
            metadata["version"] = props.version or ""

        # Calculation properties
        calc_props = wb.calculation

        metadata["calculation_mode"] = "auto"  # Default
        if calc_props:
            if hasattr(calc_props, "calcMode"):
                metadata["calculation_mode"] = calc_props.calcMode or "auto"

        # Application info
        metadata["excel_version"] = _get_excel_version(wb)

        # Locale/Language (if available)
        # Note: openpyxl doesn't directly expose locale, but we can try to infer
        metadata["locale"] = "en-US"  # Default assumption

    except Exception as e:
        logger.warning(f"Error extracting metadata: {e}")

    return metadata


def write_metadata_file(metadata: Dict[str, Any], output_path: Path) -> None:
    """
    Write metadata to a text file.

    Args:
        metadata: Metadata dictionary
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Workbook Metadata\n")
        f.write("# ==================\n\n")

        for key, value in sorted(metadata.items()):
            # Format key: replace underscores with spaces and title case
            display_key = key.replace("_", " ").title()
            f.write(f"{display_key}: {value}\n")

    logger.debug(f"Wrote metadata to: {output_path}")


def extract_structure_info(wb: Workbook) -> Dict[str, Any]:
    """
    Extract workbook structure information (sheet order, visibility, etc.).

    Args:
        wb: Openpyxl workbook object

    Returns:
        Dictionary with structure info
    """
    structure = {
        "sheets": [],
        "active_sheet": None,
    }

    try:
        # Get active sheet name
        if wb.active:
            structure["active_sheet"] = wb.active.title

        # Iterate through sheets
        for idx, sheet in enumerate(wb.worksheets, start=1):
            sheet_info = {
                "index": idx,
                "name": sheet.title,
                "sheetId": sheet.sheet_properties.sheetId if hasattr(sheet.sheet_properties, 'sheetId') else idx,
                "visible": sheet.sheet_state == "visible",
                "state": sheet.sheet_state,  # visible, hidden, veryHidden
            }

            # Tab color
            if sheet.sheet_properties.tabColor:
                tab_color = sheet.sheet_properties.tabColor
                if hasattr(tab_color, 'rgb'):
                    sheet_info["tab_color"] = f"#{tab_color.rgb}"
                elif hasattr(tab_color, 'theme'):
                    sheet_info["tab_color"] = f"theme:{tab_color.theme}"

            structure["sheets"].append(sheet_info)

    except Exception as e:
        logger.warning(f"Error extracting structure info: {e}")

    return structure


def write_structure_file(structure: Dict[str, Any], output_path: Path) -> None:
    """
    Write structure information to a text file.

    Format:
    INDEX<TAB>NAME<TAB>SHEET_ID<TAB>VISIBLE<TAB>TAB_COLOR

    Args:
        structure: Structure dictionary
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Sheet Structure\n")
        f.write("# INDEX\tNAME\tSHEET_ID\tVISIBLE\tSTATE\tTAB_COLOR\n\n")

        for sheet in structure["sheets"]:
            index = sheet["index"]
            name = sheet["name"]
            sheet_id = sheet["sheetId"]
            visible = "TRUE" if sheet["visible"] else "FALSE"
            state = sheet["state"]
            tab_color = sheet.get("tab_color", "")

            f.write(f"{index}\t{name}\t{sheet_id}\t{visible}\t{state}\t{tab_color}\n")

    logger.debug(f"Wrote structure to: {output_path}")


def extract_defined_names(wb: Workbook) -> list:
    """
    Extract defined names (named ranges) from workbook.

    Args:
        wb: Openpyxl workbook object

    Returns:
        List of defined names with their scopes and references
    """
    defined_names = []

    try:
        for name, defn in wb.defined_names.items():
            # Get destinations (cells/ranges this name refers to)
            destinations = list(defn.destinations) if hasattr(defn, 'destinations') else []

            for sheet_name, coord in destinations:
                scope = sheet_name if sheet_name else "Workbook"
                refers_to = f"{sheet_name}!{coord}" if sheet_name else coord

                defined_names.append({
                    "name": name,
                    "scope": scope,
                    "refers_to": refers_to,
                })

            # If no destinations, still record the name
            if not destinations:
                defined_names.append({
                    "name": name,
                    "scope": "Workbook",
                    "refers_to": str(defn.value) if hasattr(defn, 'value') else "",
                })

    except Exception as e:
        logger.warning(f"Error extracting defined names: {e}")

    return defined_names


def write_defined_names_file(defined_names: list, output_path: Path) -> None:
    """
    Write defined names to a text file.

    Format:
    NAME<TAB>SCOPE<TAB>REFERS_TO

    Args:
        defined_names: List of defined names
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Defined Names\n")
        f.write("# NAME\tSCOPE\tREFERS_TO\n\n")

        for item in sorted(defined_names, key=lambda x: (x["scope"], x["name"])):
            name = item["name"]
            scope = item["scope"]
            refers_to = item["refers_to"]

            f.write(f"{name}\t{scope}\t{refers_to}\n")

    logger.debug(f"Wrote defined names to: {output_path}")


def _format_datetime(dt: datetime) -> str:
    """Format datetime to ISO8601 string."""
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


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
        return str(wb.properties.version or "unknown")

    # Try to infer from file format
    # This is a best-effort guess
    return "unknown"
