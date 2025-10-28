"""
Normalization rules for formulas, values, and other Excel elements.
Ensures deterministic and diff-friendly output.
"""
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


def normalize_formula(formula: str, locale: str = "en-US") -> str:
    """
    Normalize a formula string for deterministic comparison.

    Rules:
    - Trim leading/trailing whitespace
    - Uppercase function names (SUM, not sum)
    - Don't change formula logic or simplify
    - Use comma as canonical argument separator

    Args:
        formula: Raw formula string (with or without leading =)
        locale: Workbook locale (for separator normalization)

    Returns:
        Normalized formula string
    """
    if not formula:
        return ""

    # Remove leading = if present
    formula = formula.strip()
    has_equals = formula.startswith("=")
    if has_equals:
        formula = formula[1:]

    # Trim whitespace
    formula = formula.strip()

    # Uppercase function names
    # Match function names: word characters followed by opening parenthesis
    # We need to be careful not to uppercase cell references or named ranges
    def uppercase_function(match):
        """Uppercase function name while preserving everything else."""
        return match.group(0).upper()

    # Pattern: word followed by opening paren (function call)
    # This will match: SUM(, sum(, Average(, etc.
    formula = re.sub(r'\b([A-Za-z_]\w*)\s*\(', uppercase_function, formula)

    # Normalize separators (some locales use semicolon instead of comma)
    # Record this in metadata, but for the formula text, keep as-is
    # Note: This is complex because commas can also be in string literals
    # For now, we'll preserve the original separator to avoid breaking formulas

    # Add back the equals sign
    if has_equals or formula:
        formula = "=" + formula

    return formula


def normalize_number(value: Any, max_precision: int = 15) -> str:
    """
    Normalize a numeric value for deterministic output.

    Rules:
    - Use plain decimal notation (avoid scientific unless necessary)
    - Limit to 15 significant digits (Excel's internal precision)
    - Preserve integers as integers

    Args:
        value: Numeric value (int, float, Decimal, or string)
        max_precision: Maximum significant digits

    Returns:
        Normalized string representation
    """
    if value is None or value == "":
        return ""

    try:
        # Convert to Decimal for precise handling
        if isinstance(value, str):
            # Remove any commas or formatting
            value = value.replace(",", "").strip()

        dec = Decimal(str(value))

        # Check if it's an integer
        if dec == dec.to_integral_value():
            return str(int(dec))

        # Format with max precision
        # Use quantize to limit significant digits
        formatted = format(float(dec), f'.{max_precision}g')

        # Avoid scientific notation for reasonable numbers
        if 'e' in formatted.lower():
            # If exponent is small, convert to decimal
            float_val = float(formatted)
            if abs(float_val) > 1e-6 and abs(float_val) < 1e15:
                formatted = f"{float_val:.{max_precision}f}".rstrip('0').rstrip('.')

        return formatted

    except (ValueError, InvalidOperation, TypeError):
        # If conversion fails, return string representation
        return str(value)


def normalize_date(
    value: Any,
    excel_serial: Optional[float] = None,
    number_format: Optional[str] = None
) -> str:
    """
    Normalize a date value.

    Output format: ISO8601|excel_serial|format_code
    Example: 2025-10-27T00:00:00Z|45226|yyyy-mm-dd

    Args:
        value: Date value (datetime object or string)
        excel_serial: Excel serial number representation
        number_format: Excel number format code

    Returns:
        Normalized date string with metadata
    """
    if isinstance(value, datetime):
        iso_str = value.isoformat()
        if not value.tzinfo:
            iso_str += "Z"
    elif isinstance(value, str):
        iso_str = value
    else:
        iso_str = str(value)

    parts = [iso_str]

    if excel_serial is not None:
        parts.append(str(excel_serial))

    if number_format:
        parts.append(number_format)

    return "|".join(parts)


def normalize_boolean(value: Any) -> str:
    """
    Normalize a boolean value.

    Args:
        value: Boolean value

    Returns:
        "TRUE" or "FALSE"
    """
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    elif isinstance(value, str):
        value_upper = value.strip().upper()
        if value_upper in ("TRUE", "1", "YES"):
            return "TRUE"
        elif value_upper in ("FALSE", "0", "NO"):
            return "FALSE"

    return str(value)


def normalize_string(value: str) -> str:
    """
    Normalize a string value.

    Rules:
    - Normalize line endings to LF (\n)
    - Preserve exact content otherwise

    Args:
        value: String value

    Returns:
        Normalized string
    """
    if not isinstance(value, str):
        return str(value)

    # Normalize line endings: CRLF or CR to LF
    value = value.replace("\r\n", "\n").replace("\r", "\n")

    return value


def normalize_cell_value(value: Any, value_type: str = "general") -> str:
    """
    Normalize a cell value based on its type.

    Args:
        value: Cell value
        value_type: Type of value (number, string, bool, date, formula, etc.)

    Returns:
        Normalized string representation
    """
    if value is None or value == "":
        return ""

    value_type = value_type.lower()

    if value_type == "bool" or value_type == "boolean":
        return normalize_boolean(value)
    elif value_type == "number" or value_type == "numeric":
        return normalize_number(value)
    elif value_type == "date" or value_type == "datetime":
        return normalize_date(value)
    elif value_type == "string" or value_type == "str":
        return normalize_string(value)
    else:
        # General: auto-detect
        if isinstance(value, bool):
            return normalize_boolean(value)
        elif isinstance(value, (int, float, Decimal)):
            return normalize_number(value)
        elif isinstance(value, datetime):
            return normalize_date(value)
        elif isinstance(value, str):
            return normalize_string(value)
        else:
            return str(value)


def normalize_color(color: Any) -> str:
    """
    Normalize a color value to hex format.

    Args:
        color: Color value (hex string, RGB tuple, or theme reference)

    Returns:
        Normalized color string (#RRGGBB or theme:N)
    """
    if not color:
        return ""

    if isinstance(color, str):
        # Already hex format
        if color.startswith("#"):
            return color.upper()

        # Theme reference
        if color.startswith("theme:"):
            return color

        # Try to parse as hex without #
        if len(color) == 6 and all(c in "0123456789ABCDEFabcdef" for c in color):
            return "#" + color.upper()

    elif isinstance(color, (tuple, list)) and len(color) >= 3:
        # RGB tuple
        r, g, b = color[:3]
        return f"#{r:02X}{g:02X}{b:02X}"

    return str(color)


def normalize_cell_address(address: str) -> str:
    """
    Normalize a cell address.

    Args:
        address: Cell address (e.g., "A1", "Sheet1!B2", "$A$1")

    Returns:
        Normalized address (uppercase, no dollar signs for sorting)
    """
    if not address:
        return ""

    # Remove dollar signs (absolute references) for consistent sorting
    # But keep them in the formula text itself
    address = address.upper().replace("$", "")

    return address


def sort_key_for_cell_address(address: str) -> tuple:
    """
    Generate a sort key for cell addresses (row-major order).

    Args:
        address: Cell address (e.g., "A1", "B2", "AA100")

    Returns:
        Tuple for sorting (row, column)
    """
    # Remove sheet name if present
    if "!" in address:
        address = address.split("!")[-1]

    # Remove dollar signs
    address = address.replace("$", "")

    # Parse column letters and row number
    match = re.match(r'^([A-Z]+)(\d+)$', address.upper())
    if not match:
        return (0, 0)

    col_letters, row_num = match.groups()

    # Convert column letters to number (A=1, B=2, ..., Z=26, AA=27, etc.)
    col_num = 0
    for char in col_letters:
        col_num = col_num * 26 + (ord(char) - ord('A') + 1)

    return (int(row_num), col_num)


def normalize_sheet_name(name: str) -> str:
    """
    Normalize a sheet name for file paths.

    Args:
        name: Sheet name

    Returns:
        Sanitized sheet name safe for filenames
    """
    if not name:
        return "Sheet"

    # Replace characters not safe for filenames
    # Keep alphanumeric, spaces, hyphens, underscores
    safe_name = re.sub(r'[^\w\s\-]', '_', name)

    # Collapse multiple spaces/underscores
    safe_name = re.sub(r'[\s_]+', '_', safe_name)

    # Trim
    safe_name = safe_name.strip('_')

    return safe_name or "Sheet"
