"""
VBA macro extraction from Excel workbooks.

Uses oletools to extract VBA code, including from password-protected macros.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional

try:
    from oletools.olevba import VBA_Parser
    OLETOOLS_AVAILABLE = True
except ImportError:
    OLETOOLS_AVAILABLE = False
    logging.warning("oletools not available - VBA extraction disabled")

logger = logging.getLogger(__name__)


def extract_vba(file_path: Path) -> Optional[Dict[str, any]]:
    """
    Extract VBA macros from Excel file.

    Works with:
    - .xlsm (macro-enabled workbook)
    - .xls (legacy Excel)
    - .xlsb (binary workbook)

    Can extract even from password-protected VBA projects.

    Args:
        file_path: Path to Excel file

    Returns:
        Dictionary with VBA information or None if no macros
    """
    if not OLETOOLS_AVAILABLE:
        logger.warning("oletools not installed - skipping VBA extraction")
        return None

    logger.debug(f"Extracting VBA from: {file_path}")

    try:
        vba_parser = VBA_Parser(str(file_path))

        # Check if macros exist
        if not vba_parser.detect_vba_macros():
            logger.info("✓ No VBA macros detected")
            vba_parser.close()
            return None

        # Extract all modules
        modules = []
        for (filename, stream_path, vba_filename, vba_code) in vba_parser.extract_macros():
            if vba_code:
                module_info = {
                    'filename': vba_filename or 'Unknown',
                    'stream_path': stream_path or '',
                    'code': vba_code
                }
                modules.append(module_info)
                logger.debug(f"Extracted VBA module: {vba_filename}")

        vba_parser.close()

        if not modules:
            logger.info("✓ No VBA code extracted")
            return None

        vba_info = {
            'has_macros': True,
            'module_count': len(modules),
            'modules': modules
        }

        logger.info(f"✓ Extracted {len(modules)} VBA modules")
        return vba_info

    except Exception as e:
        logger.error(f"Error extracting VBA: {e}", exc_info=True)
        return None


def write_vba_files(vba_info: Dict[str, any], output_dir: Path) -> List[Path]:
    """
    Write VBA modules to separate files.

    Each module is written to: <module_name>.vba

    Args:
        vba_info: VBA information dictionary from extract_vba()
        output_dir: Directory to write VBA files

    Returns:
        List of created file paths
    """
    if not vba_info or not vba_info.get('modules'):
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    created_files = []

    for module in vba_info['modules']:
        module_name = module['filename']
        module_code = module['code']

        # Sanitise filename
        safe_name = _sanitise_filename(module_name)
        if not safe_name.endswith('.vba'):
            safe_name += '.vba'

        output_path = output_dir / safe_name

        # Write module code
        with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(f'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\n')
            f.write(f'\'\' VBA Module: {module_name}\n')
            f.write(f'\'\' Stream: {module["stream_path"]}\n')
            f.write(f'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\'\n\n')
            f.write(module_code)

        created_files.append(output_path)
        logger.debug(f"Wrote VBA module: {output_path}")

    logger.info(f"✓ Wrote {len(created_files)} VBA files to {output_dir}")
    return created_files


def write_vba_summary(vba_info: Dict[str, any], output_path: Path) -> None:
    """
    Write VBA summary file.

    Lists all modules with basic statistics.

    Args:
        vba_info: VBA information dictionary
        output_path: Path to summary file
    """
    if not vba_info:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# VBA Macros Summary\n')
        f.write('# ==================\n\n')

        f.write(f"Has Macros: {'yes' if vba_info['has_macros'] else 'no'}\n")
        f.write(f"Module Count: {vba_info['module_count']}\n\n")

        if vba_info.get('modules'):
            f.write('Modules:\n')
            for module in vba_info['modules']:
                module_name = module['filename']
                code_lines = module['code'].count('\n')
                f.write(f"  - {module_name} ({code_lines} lines)\n")

    logger.debug(f"Wrote VBA summary: {output_path}")


def _sanitise_filename(filename: str) -> str:
    """
    Sanitise filename for safe writing.

    Args:
        filename: Original filename

    Returns:
        Sanitised filename
    """
    # Replace problematic characters
    replacements = {
        '/': '_',
        '\\': '_',
        ':': '_',
        '*': '_',
        '?': '_',
        '"': '_',
        '<': '_',
        '>': '_',
        '|': '_',
    }

    sanitised = filename
    for char, replacement in replacements.items():
        sanitised = sanitised.replace(char, replacement)

    # Remove leading/trailing spaces and dots
    sanitised = sanitised.strip(). strip('.')

    # Ensure not empty
    if not sanitised:
        sanitised = 'module'

    return sanitised
