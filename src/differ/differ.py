"""
Excel Differ - Compare two Excel files

This module provides functionality to diff two Excel files by:
1. Flattening both files using a flattener
2. Comparing the flattened outputs
3. Returning structured diff results
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import filecmp
import difflib
from src.interfaces import FlattenerInterface


class Differ:
    """
    Compare two Excel files by flattening and diffing.

    This is an on-demand differ that takes two Excel files,
    flattens them, and produces a structured diff.
    """

    def __init__(self, flattener: FlattenerInterface):
        """
        Initialize differ with a flattener.

        Args:
            flattener: Flattener instance to use for flattening Excel files
        """
        self.flattener = flattener

    def diff_files(
        self,
        file1: Path,
        file2: Path,
        output_format: str = 'json'
    ) -> Dict[str, Any]:
        """
        Compare two Excel files.

        Args:
            file1: Path to first Excel file
            file2: Path to second Excel file
            output_format: Output format ('json' or 'html')

        Returns:
            Dictionary containing diff results:
            {
                'file1': str,
                'file2': str,
                'files_compared': int,
                'files_different': int,
                'files_only_in_file1': List[str],
                'files_only_in_file2': List[str],
                'differences': List[Dict],
                'success': bool,
                'errors': List[str]
            }
        """
        try:
            # Flatten both files
            result1 = self.flattener.flatten(file1)
            result2 = self.flattener.flatten(file2)

            if not result1.success:
                return {
                    'success': False,
                    'errors': [f"Failed to flatten {file1}: {', '.join(result1.errors)}"]
                }

            if not result2.success:
                return {
                    'success': False,
                    'errors': [f"Failed to flatten {file2}: {', '.join(result2.errors)}"]
                }

            # Compare flattened directories
            diff_result = self._compare_directories(
                result1.flat_root,
                result2.flat_root,
                file1.name,
                file2.name
            )

            return diff_result

        except Exception as e:
            return {
                'success': False,
                'errors': [f"Diff failed: {str(e)}"]
            }

    def _compare_directories(
        self,
        dir1: Path,
        dir2: Path,
        file1_name: str,
        file2_name: str
    ) -> Dict[str, Any]:
        """
        Compare two flattened directories.

        Returns structured diff results.
        """
        # Use filecmp to compare directories
        dcmp = filecmp.dircmp(str(dir1), str(dir2))

        differences = []
        files_compared = 0
        files_different = 0

        # Compare common files
        for filename in dcmp.common_files:
            files_compared += 1
            file1_path = dir1 / filename
            file2_path = dir2 / filename

            if not filecmp.cmp(file1_path, file2_path, shallow=False):
                files_different += 1
                # Get detailed diff
                diff = self._diff_files(file1_path, file2_path, filename)
                differences.append(diff)

        # Recursively compare subdirectories
        for subdir in dcmp.common_dirs:
            subresult = self._compare_directories(
                dir1 / subdir,
                dir2 / subdir,
                file1_name,
                file2_name
            )
            differences.extend(subresult['differences'])
            files_compared += subresult['files_compared']
            files_different += subresult['files_different']

        return {
            'file1': file1_name,
            'file2': file2_name,
            'files_compared': files_compared,
            'files_different': files_different,
            'files_only_in_file1': dcmp.left_only,
            'files_only_in_file2': dcmp.right_only,
            'differences': differences,
            'success': True,
            'errors': []
        }

    def _diff_files(self, file1: Path, file2: Path, filename: str) -> Dict[str, Any]:
        """
        Generate detailed diff for two text files.

        Returns diff information including unified diff.
        """
        try:
            with open(file1, 'r', encoding='utf-8') as f1:
                lines1 = f1.readlines()
            with open(file2, 'r', encoding='utf-8') as f2:
                lines2 = f2.readlines()

            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                lines1,
                lines2,
                fromfile=f"file1/{filename}",
                tofile=f"file2/{filename}",
                lineterm=''
            ))

            return {
                'filename': filename,
                'lines_added': sum(1 for line in diff_lines if line.startswith('+')),
                'lines_removed': sum(1 for line in diff_lines if line.startswith('-')),
                'diff': '\n'.join(diff_lines)
            }
        except UnicodeDecodeError:
            # Binary file, just note that it's different
            return {
                'filename': filename,
                'binary': True,
                'diff': 'Binary files differ'
            }
