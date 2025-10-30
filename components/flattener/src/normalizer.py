"""
Normalisation utilities for Excel data.

Philosophy: Minimal normalisation - extract as-is from Excel.
Only normalise where absolutely necessary for consistent diffs.
"""
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Text Normalisation
# ============================================================================

def normalise_line_endings(text: str) -> str:
    """
    Normalise line endings to LF (Unix style).

    Converts CRLF (\\r\\n) and CR (\\r) to LF (\\n).

    Args:
        text: String with any line endings

    Returns:
        String with LF line endings only
    """
    if not isinstance(text, str):
        return str(text)

    # CRLF -> LF, then CR -> LF
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    return text


def normalise_string_value(value: Any) -> str:
    """
    Normalise a string value for output.

    Only normalises line endings. Everything else preserved as-is.

    Args:
        value: Value to normalise (typically a string)

    Returns:
        Normalised string
    """
    if value is None or value == '':
        return ''

    if not isinstance(value, str):
        value = str(value)

    # Only normalise line endings
    return normalise_line_endings(value)


# ============================================================================
# Number Normalisation
# ============================================================================

def normalise_number_value(value: Any) -> str:
    """
    Normalise a number value for output.

    Extract with full precision as stored by Excel.
    NO truncation, NO format changes.

    Args:
        value: Numeric value (int, float, etc.)

    Returns:
        String representation with full precision
    """
    if value is None or value == '':
        return ''

    # Check if integer (no decimal part)
    if isinstance(value, (int, float)):
        if isinstance(value, int) or value == int(value):
            return str(int(value))
        else:
            # Float with decimal part - preserve full precision
            return str(value)

    return str(value)


# ============================================================================
# Date Normalisation
# ============================================================================

def normalise_date_value(value: Any) -> str:
    """
    Normalise a date/datetime value to ISO8601 with timezone.

    Format: YYYY-MM-DDTHH:MM:SSZ (UTC)

    Args:
        value: Date or datetime value

    Returns:
        ISO8601 string with Z timezone
    """
    if value is None or value == '':
        return ''

    if isinstance(value, datetime):
        # Format as ISO8601 with Z (UTC)
        if value.tzinfo:
            # Has timezone, use it
            iso_str = value.isoformat()
        else:
            # No timezone, assume UTC and add Z
            iso_str = value.isoformat() + 'Z'
        return iso_str

    # Not a datetime, return as-is
    return str(value)


# ============================================================================
# Boolean Normalisation
# ============================================================================

def normalise_boolean_value(value: Any) -> str:
    """
    Normalise a boolean value.

    Uses Excel's format: TRUE or FALSE (uppercase).

    Args:
        value: Boolean value

    Returns:
        'TRUE' or 'FALSE'
    """
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'

    # Try to interpret as boolean
    if isinstance(value, str):
        value_upper = value.strip().upper()
        if value_upper in ('TRUE', '1', 'YES'):
            return 'TRUE'
        elif value_upper in ('FALSE', '0', 'NO'):
            return 'FALSE'

    return str(value)


# ============================================================================
# Cell Value Normalisation (Auto-detect Type)
# ============================================================================

def normalise_cell_value(value: Any, value_type: str = 'auto') -> str:
    """
    Normalise a cell value based on its type.

    Args:
        value: Cell value
        value_type: Type hint ('auto', 'number', 'string', 'bool', 'date')

    Returns:
        Normalised string representation
    """
    if value is None or value == '':
        return ''

    # Auto-detect type if not specified
    if value_type == 'auto':
        if isinstance(value, bool):
            value_type = 'bool'
        elif isinstance(value, (int, float)):
            value_type = 'number'
        elif isinstance(value, datetime):
            value_type = 'date'
        elif isinstance(value, str):
            value_type = 'string'
        else:
            # Unknown type, treat as string
            value_type = 'string'

    # Apply appropriate normalisation
    if value_type == 'bool':
        return normalise_boolean_value(value)
    elif value_type == 'number':
        return normalise_number_value(value)
    elif value_type == 'date':
        return normalise_date_value(value)
    elif value_type == 'string':
        return normalise_string_value(value)
    else:
        # Fallback: string conversion
        return normalise_string_value(value)


# ============================================================================
# Formula Normalisation
# ============================================================================

def normalise_formula(formula: str) -> str:
    """
    Normalise a formula for output.

    MINIMAL normalisation: Extract exactly as stored in Excel.
    - Keep original case (sum vs SUM)
    - Keep original spacing
    - Keep original structure

    Only ensure leading = is present.

    Args:
        formula: Formula string (may or may not have leading =)

    Returns:
        Normalised formula with leading =
    """
    if not formula:
        return ''

    formula = formula.strip()

    # Ensure leading =
    if not formula.startswith('='):
        formula = '=' + formula

    return formula


# ============================================================================
# Colour Normalisation
# ============================================================================

def normalise_colour(colour: Any) -> str:
    """
    Normalise a colour value to hex format or theme reference.

    Args:
        colour: Colour object from openpyxl

    Returns:
        Hex colour (#RRGGBB) or theme reference (theme:N)
    """
    if not colour:
        return ''

    # Handle openpyxl colour objects
    if hasattr(colour, 'rgb') and colour.rgb:
        rgb = colour.rgb
        if isinstance(rgb, str) and len(rgb) >= 6:
            # Remove alpha channel if present (AARRGGBB -> RRGGBB)
            if len(rgb) == 8:
                rgb = rgb[2:]
            return f"#{rgb.upper()}"

    if hasattr(colour, 'theme') and colour.theme is not None:
        return f"theme:{colour.theme}"

    if hasattr(colour, 'indexed') and colour.indexed is not None:
        return f"indexed:{colour.indexed}"

    return ''


# ============================================================================
# Sheet Name Normalisation (for Filenames)
# ============================================================================

def normalise_sheet_name(name: str) -> str:
    """
    Normalise a sheet name for use in filenames.

    Replaces characters that are invalid in filenames.

    Args:
        name: Sheet name

    Returns:
        Sanitised sheet name safe for filenames
    """
    if not name:
        return 'Sheet'

    # Import sanitise function from utils
    from .utils import sanitise_filename

    return sanitise_filename(name)


# ============================================================================
# Sorting Utilities
# ============================================================================

def sort_rows_by_address(rows: list) -> list:
    """
    Sort rows by cell address in row-major order.

    Each row should be a dictionary with 'address' key.

    Args:
        rows: List of dictionaries with 'address' key

    Returns:
        Sorted list
    """
    from .utils import sort_key_for_cell_address

    return sorted(rows, key=lambda x: sort_key_for_cell_address(x['address']))
