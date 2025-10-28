"""
VBA module extraction using oletools.
Extracts VBA code from Excel workbooks while preserving raw vbaProject.bin.
"""
import shutil
from pathlib import Path
from typing import Dict, List
import logging
import zipfile

from src.engine.flattener.manifest import Manifest

logger = logging.getLogger(__name__)


def extract_vba_modules(
    workbook_path: Path,
    vba_dir: Path,
    manifest: Manifest,
) -> None:
    """
    Extract VBA modules from an Excel workbook.

    Args:
        workbook_path: Path to workbook file (XLSM or XLSB)
        vba_dir: Directory to write VBA files
        manifest: Manifest object to add warnings
    """
    logger.info(f"Extracting VBA from: {workbook_path}")

    # First, try to extract raw vbaProject.bin
    vba_bin_extracted = _extract_vba_project_bin(workbook_path, vba_dir, manifest)

    if not vba_bin_extracted:
        logger.info("No VBA project found in workbook")
        (vba_dir / "no_vba.txt").write_text("# No VBA project found in this workbook\n")
        return

    # Try to extract individual modules using oletools
    try:
        from oletools.olevba import VBA_Parser

        logger.debug("Parsing VBA using oletools...")
        vba_parser = VBA_Parser(str(workbook_path))

        if not vba_parser.detect_vba_macros():
            logger.info("No VBA macros detected by oletools")
            manifest.add_warning("VBA project present but no macros detected")
            return

        # Extract modules
        modules_extracted = 0
        for (filename, stream_path, vba_filename, vba_code) in vba_parser.extract_macros():
            if vba_code:
                module_name = vba_filename or f"Module_{modules_extracted + 1}"

                # Determine file extension based on module type
                ext = _get_module_extension(module_name, vba_code)

                module_path = vba_dir / f"{module_name}{ext}"

                # Write module code exactly as extracted
                with open(module_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(vba_code)

                logger.debug(f"Extracted VBA module: {module_name}{ext}")
                modules_extracted += 1

        vba_parser.close()

        if modules_extracted > 0:
            logger.info(f"Extracted {modules_extracted} VBA modules")
        else:
            manifest.add_warning("VBA project present but no modules could be extracted")

    except ImportError:
        logger.warning("oletools not available, cannot extract VBA modules")
        manifest.add_warning("VBA extraction skipped: oletools not installed")
        (vba_dir / "vba_extraction_skipped.txt").write_text(
            "# VBA extraction requires oletools library\n"
            "# Install with: pip install oletools\n"
        )

    except Exception as e:
        logger.warning(f"Failed to extract VBA modules: {e}")

        if "password" in str(e).lower() or "protected" in str(e).lower():
            manifest.add_warning("VBA project is password protected")
            (vba_dir / "VBA_PROJECT_PROTECTED.txt").write_text(
                "# VBA project is password protected and cannot be extracted\n"
            )
        else:
            manifest.add_warning(f"VBA extraction failed: {e}")
            (vba_dir / "vba_extraction_failed.txt").write_text(
                f"# VBA extraction failed: {e}\n"
            )


def _extract_vba_project_bin(
    workbook_path: Path,
    vba_dir: Path,
    manifest: Manifest,
) -> bool:
    """
    Extract raw vbaProject.bin from the workbook.

    XLSM/XLSX files are ZIP archives. We can extract vbaProject.bin directly.

    Args:
        workbook_path: Path to workbook
        vba_dir: Directory to write VBA files
        manifest: Manifest object

    Returns:
        True if vbaProject.bin was found and extracted, False otherwise
    """
    try:
        with zipfile.ZipFile(workbook_path, 'r') as zf:
            # Look for vbaProject.bin in the ZIP
            vba_bin_path = "xl/vbaProject.bin"

            if vba_bin_path in zf.namelist():
                # Extract vbaProject.bin
                output_path = vba_dir / "vbaProject.bin"
                with zf.open(vba_bin_path) as source, open(output_path, 'wb') as target:
                    target.write(source.read())

                logger.info(f"Extracted vbaProject.bin to: {output_path}")
                return True
            else:
                logger.debug("No vbaProject.bin found in workbook ZIP")
                return False

    except zipfile.BadZipFile:
        logger.warning(f"File is not a valid ZIP archive: {workbook_path}")
        return False
    except Exception as e:
        logger.warning(f"Failed to extract vbaProject.bin: {e}")
        return False


def _get_module_extension(module_name: str, code: str) -> str:
    """
    Determine the appropriate file extension for a VBA module.

    Args:
        module_name: Module name
        code: Module code

    Returns:
        File extension (.bas, .cls, .frm, etc.)
    """
    module_name_lower = module_name.lower()

    # Check module name first
    if "thisworkbook" in module_name_lower:
        return ".bas"
    if "sheet" in module_name_lower and module_name_lower.startswith("sheet"):
        return ".bas"
    if "userform" in module_name_lower:
        return ".frm"

    # Check code content
    code_lower = code.lower()

    if "attribute vb_name" in code_lower:
        # It's likely a class or form
        if "userform" in code_lower:
            return ".frm"
        if "class" in module_name_lower:
            return ".cls"

    # Check for class module indicators
    if code.strip().startswith("VERSION") or "Begin {" in code:
        return ".frm"  # UserForm

    if "option explicit" in code_lower or "public" in code_lower or "private" in code_lower:
        # Standard module
        if "class" in module_name_lower:
            return ".cls"
        return ".bas"

    # Default to .bas for standard modules
    return ".bas"
