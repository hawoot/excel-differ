"""
JSON Formatter for diff results

Formats diff results as JSON for programmatic consumption.
"""

import json
from typing import Dict, Any


class JSONFormatter:
    """Format diff results as JSON"""

    def format(self, diff_result: Dict[str, Any], pretty: bool = True) -> str:
        """
        Format diff result as JSON string.

        Args:
            diff_result: Diff result dictionary from Differ
            pretty: If True, format with indentation for readability

        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(diff_result, indent=2)
        else:
            return json.dumps(diff_result)

    def save(self, diff_result: Dict[str, Any], output_path: str, pretty: bool = True):
        """
        Save diff result to JSON file.

        Args:
            diff_result: Diff result dictionary from Differ
            output_path: Path where to save JSON file
            pretty: If True, format with indentation
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(diff_result, f, indent=2)
            else:
                json.dump(diff_result, f)
