"""
Generate structured JSON diffs from snapshot comparisons.
Produces typed change objects for different categories.
"""
import json
from pathlib import Path
from typing import Dict, List, Any
import logging

from src.engine.differ.compare import SnapshotComparison

logger = logging.getLogger(__name__)


def generate_json_diff(comparison: SnapshotComparison) -> Dict[str, Any]:
    """
    Generate structured JSON diff from snapshot comparison.

    Args:
        comparison: SnapshotComparison object

    Returns:
        Dict containing diff_json array and summary
    """
    changes = []

    # Detect sheet-level changes
    changes.extend(_detect_sheet_changes(comparison))

    # Detect formula changes
    changes.extend(_detect_formula_changes(comparison))

    # Detect hard-coded value changes
    changes.extend(_detect_value_hardcoded_changes(comparison))

    # Detect evaluated value changes (if present)
    changes.extend(_detect_value_evaluated_changes(comparison))

    # Detect VBA changes
    changes.extend(_detect_vba_changes(comparison))

    # Detect format changes
    changes.extend(_detect_format_changes(comparison))

    # Detect other file-level changes
    changes.extend(_detect_file_changes(comparison))

    # Generate summary
    summary = _generate_summary(changes)

    return {
        "diff_json": changes,
        "summary": summary,
    }


def _detect_sheet_changes(comparison: SnapshotComparison) -> List[Dict[str, Any]]:
    """Detect sheet additions, removals, and renames."""
    changes = []

    manifest_a = comparison.manifest_a
    manifest_b = comparison.manifest_b

    if not manifest_a or not manifest_b:
        return changes

    sheets_a = {s["name"]: s for s in manifest_a.sheets}
    sheets_b = {s["name"]: s for s in manifest_b.sheets}

    names_a = set(sheets_a.keys())
    names_b = set(sheets_b.keys())

    # Added sheets
    for name in sorted(names_b - names_a):
        changes.append({
            "category": "sheet",
            "action": "added",
            "new_name": name,
            "details": sheets_b[name],
        })

    # Removed sheets
    for name in sorted(names_a - names_b):
        changes.append({
            "category": "sheet",
            "action": "removed",
            "old_name": name,
            "details": sheets_a[name],
        })

    # Renamed sheets (detect by sheetId)
    # This is complex - for now, skip rename detection

    return changes


def _detect_formula_changes(comparison: SnapshotComparison) -> List[Dict[str, Any]]:
    """Detect formula changes across all sheets."""
    changes = []

    # Find all formula files
    formula_files_a = [f for f in comparison.files_a.keys() if ".formulas.txt" in f]
    formula_files_b = [f for f in comparison.files_b.keys() if ".formulas.txt" in f]

    all_formula_files = set(formula_files_a) | set(formula_files_b)

    for file_path in sorted(all_formula_files):
        # Extract sheet name from file path
        # Format: sheets/01.SheetName.formulas.txt
        sheet_name = _extract_sheet_name(file_path)

        added, removed, modified = comparison.compare_tabular_file(file_path)

        for cell, formula in added:
            changes.append({
                "category": "formula",
                "action": "added",
                "sheet": sheet_name,
                "cell": cell,
                "new": formula,
            })

        for cell, formula in removed:
            changes.append({
                "category": "formula",
                "action": "removed",
                "sheet": sheet_name,
                "cell": cell,
                "old": formula,
            })

        for cell, old_formula, new_formula in modified:
            changes.append({
                "category": "formula",
                "sheet": sheet_name,
                "cell": cell,
                "old": old_formula,
                "new": new_formula,
            })

    return changes


def _detect_value_hardcoded_changes(comparison: SnapshotComparison) -> List[Dict[str, Any]]:
    """Detect hard-coded value changes."""
    changes = []

    value_files_a = [f for f in comparison.files_a.keys() if ".values_hardcoded.txt" in f]
    value_files_b = [f for f in comparison.files_b.keys() if ".values_hardcoded.txt" in f]

    all_value_files = set(value_files_a) | set(value_files_b)

    for file_path in sorted(all_value_files):
        sheet_name = _extract_sheet_name(file_path)

        added, removed, modified = comparison.compare_tabular_file(file_path)

        for cell, value in added:
            changes.append({
                "category": "value_hardcoded",
                "action": "added",
                "sheet": sheet_name,
                "cell": cell,
                "new": value,
            })

        for cell, value in removed:
            changes.append({
                "category": "value_hardcoded",
                "action": "removed",
                "sheet": sheet_name,
                "cell": cell,
                "old": value,
            })

        for cell, old_value, new_value in modified:
            changes.append({
                "category": "value_hardcoded",
                "sheet": sheet_name,
                "cell": cell,
                "old": old_value,
                "new": new_value,
            })

    return changes


def _detect_value_evaluated_changes(comparison: SnapshotComparison) -> List[Dict[str, Any]]:
    """Detect evaluated value changes (if present)."""
    changes = []

    value_files_a = [f for f in comparison.files_a.keys() if ".values_evaluated.txt" in f]
    value_files_b = [f for f in comparison.files_b.keys() if ".values_evaluated.txt" in f]

    all_value_files = set(value_files_a) | set(value_files_b)

    for file_path in sorted(all_value_files):
        sheet_name = _extract_sheet_name(file_path)

        added, removed, modified = comparison.compare_tabular_file(file_path)

        for cell, value in added:
            changes.append({
                "category": "value_evaluated",
                "action": "added",
                "sheet": sheet_name,
                "cell": cell,
                "new": value,
                "note": "cached",
            })

        for cell, value in removed:
            changes.append({
                "category": "value_evaluated",
                "action": "removed",
                "sheet": sheet_name,
                "cell": cell,
                "old": value,
                "note": "cached",
            })

        for cell, old_value, new_value in modified:
            changes.append({
                "category": "value_evaluated",
                "sheet": sheet_name,
                "cell": cell,
                "old": old_value,
                "new": new_value,
                "note": "cached",
            })

    return changes


def _detect_vba_changes(comparison: SnapshotComparison) -> List[Dict[str, Any]]:
    """Detect VBA module changes."""
    changes = []

    vba_files_a = [f for f in comparison.files_a.keys() if f.startswith("vba/") and f.endswith((".bas", ".cls", ".frm"))]
    vba_files_b = [f for f in comparison.files_b.keys() if f.startswith("vba/") and f.endswith((".bas", ".cls", ".frm"))]

    all_vba_files = set(vba_files_a) | set(vba_files_b)

    for file_path in sorted(all_vba_files):
        module_name = Path(file_path).stem

        if file_path in vba_files_a and file_path not in vba_files_b:
            # Removed
            changes.append({
                "category": "vba",
                "action": "removed",
                "module": module_name,
            })

        elif file_path in vba_files_b and file_path not in vba_files_a:
            # Added
            changes.append({
                "category": "vba",
                "action": "added",
                "module": module_name,
            })

        else:
            # Modified?
            if comparison.files_a[file_path] != comparison.files_b[file_path]:
                diff_text = comparison.get_file_diff(file_path, context_lines=3)
                changes.append({
                    "category": "vba",
                    "action": "modified",
                    "module": module_name,
                    "diff": diff_text or "(binary change)",
                })

    return changes


def _detect_format_changes(comparison: SnapshotComparison) -> List[Dict[str, Any]]:
    """Detect cell format changes."""
    changes = []

    format_files_a = [f for f in comparison.files_a.keys() if ".cell_formats.txt" in f]
    format_files_b = [f for f in comparison.files_b.keys() if ".cell_formats.txt" in f]

    all_format_files = set(format_files_a) | set(format_files_b)

    # Count total format changes but don't include every cell
    # (too verbose for JSON output)
    total_format_changes = 0

    for file_path in sorted(all_format_files):
        sheet_name = _extract_sheet_name(file_path)

        added, removed, modified = comparison.compare_tabular_file(file_path)

        total_format_changes += len(added) + len(removed) + len(modified)

    if total_format_changes > 0:
        changes.append({
            "category": "format",
            "action": "modified",
            "details": f"{total_format_changes} cell format changes across all sheets",
        })

    return changes


def _detect_file_changes(comparison: SnapshotComparison) -> List[Dict[str, Any]]:
    """Detect generic file-level changes."""
    changes = []

    changed_files = comparison.get_changed_files()

    # Report on significant file changes (not already covered above)
    skip_patterns = [
        ".formulas.txt",
        ".values_hardcoded.txt",
        ".values_evaluated.txt",
        ".cell_formats.txt",
        "vba/",
    ]

    for file_path in changed_files["modified"]:
        # Skip files we've already processed
        if any(pattern in file_path for pattern in skip_patterns):
            continue

        # Report other file changes
        diff_text = comparison.get_file_diff(file_path, context_lines=3)

        changes.append({
            "category": "file",
            "action": "modified",
            "path": file_path,
            "diff": diff_text or "(binary or large change)",
        })

    return changes


def _generate_summary(changes: List[Dict[str, Any]]) -> Dict[str, int]:
    """Generate summary statistics from changes."""
    summary = {
        "sheets_added": 0,
        "sheets_removed": 0,
        "formulas_changed": 0,
        "values_hardcoded_changed": 0,
        "values_evaluated_changed": 0,
        "vba_modules_changed": 0,
        "format_changes": 0,
        "other_changes": 0,
    }

    for change in changes:
        category = change.get("category")

        if category == "sheet":
            if change.get("action") == "added":
                summary["sheets_added"] += 1
            elif change.get("action") == "removed":
                summary["sheets_removed"] += 1

        elif category == "formula":
            summary["formulas_changed"] += 1

        elif category == "value_hardcoded":
            summary["values_hardcoded_changed"] += 1

        elif category == "value_evaluated":
            summary["values_evaluated_changed"] += 1

        elif category == "vba":
            summary["vba_modules_changed"] += 1

        elif category == "format":
            summary["format_changes"] += 1

        else:
            summary["other_changes"] += 1

    return summary


def _extract_sheet_name(file_path: str) -> str:
    """
    Extract sheet name from file path.

    Example: sheets/01.SheetName.formulas.txt -> SheetName
    """
    file_name = Path(file_path).name

    # Remove prefix (01.) and suffix (.formulas.txt, etc.)
    parts = file_name.split(".")

    if len(parts) >= 3:
        # Format: 01.SheetName.formulas.txt
        # Sheet name is parts[1]
        return parts[1]

    return file_name
