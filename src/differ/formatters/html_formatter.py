"""
HTML Formatter for diff results (FUTURE)

This will format diff results as an HTML page with syntax highlighting.
"""

from typing import Dict, Any


class HTMLFormatter:
    """Format diff results as HTML (to be implemented)"""

    def format(self, diff_result: Dict[str, Any]) -> str:
        """
        Format diff result as HTML string.

        Args:
            diff_result: Diff result dictionary from Differ

        Returns:
            HTML string
        """
        # TODO: Implement HTML formatting
        raise NotImplementedError("HTML formatter not yet implemented")

    def save(self, diff_result: Dict[str, Any], output_path: str):
        """
        Save diff result to HTML file.

        Args:
            diff_result: Diff result dictionary from Differ
            output_path: Path where to save HTML file
        """
        # TODO: Implement HTML file saving
        raise NotImplementedError("HTML formatter not yet implemented")
