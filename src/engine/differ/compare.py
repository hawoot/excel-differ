"""
Folder-to-folder comparison for flattened snapshots.
Detects file changes, additions, and deletions.
"""
import hashlib
import difflib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
import json

from src.engine.flattener.manifest import Manifest

logger = logging.getLogger(__name__)


class SnapshotComparison:
    """
    Compares two flattened Excel snapshots.
    """

    def __init__(self, snapshot_a: Path, snapshot_b: Path):
        """
        Initialize comparison.

        Args:
            snapshot_a: Path to first snapshot directory
            snapshot_b: Path to second snapshot directory
        """
        self.snapshot_a = snapshot_a
        self.snapshot_b = snapshot_b

        # Load manifests
        self.manifest_a = self._load_manifest(snapshot_a)
        self.manifest_b = self._load_manifest(snapshot_b)

        # File inventories (path -> sha256)
        self.files_a = self._build_file_inventory(snapshot_a, self.manifest_a)
        self.files_b = self._build_file_inventory(snapshot_b, self.manifest_b)

    def _load_manifest(self, snapshot_dir: Path) -> Optional[Manifest]:
        """Load manifest from snapshot directory."""
        manifest_path = snapshot_dir / "manifest.json"
        if manifest_path.exists():
            return Manifest.load(manifest_path)
        return None

    def _build_file_inventory(
        self, snapshot_dir: Path, manifest: Optional[Manifest]
    ) -> Dict[str, str]:
        """
        Build file inventory from manifest or by scanning directory.

        Returns:
            Dict mapping relative path to sha256 hash
        """
        inventory = {}

        if manifest and manifest.files:
            # Use manifest
            for file_info in manifest.files:
                inventory[file_info["path"]] = file_info["sha256"]
        else:
            # Scan directory
            for file_path in snapshot_dir.rglob("*"):
                if file_path.is_file() and file_path.name != "manifest.json":
                    rel_path = str(file_path.relative_to(snapshot_dir)).replace("\\", "/")
                    file_hash = self._hash_file(file_path)
                    inventory[rel_path] = file_hash

        return inventory

    def _hash_file(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_changed_files(self) -> Dict[str, List[str]]:
        """
        Get lists of added, removed, and modified files.

        Returns:
            Dict with keys: added, removed, modified
        """
        all_files_a = set(self.files_a.keys())
        all_files_b = set(self.files_b.keys())

        added = sorted(all_files_b - all_files_a)
        removed = sorted(all_files_a - all_files_b)

        # Modified: files that exist in both but have different hashes
        common_files = all_files_a & all_files_b
        modified = sorted([
            f for f in common_files
            if self.files_a[f] != self.files_b[f]
        ])

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
        }

    def get_file_diff(
        self, relative_path: str, context_lines: int = 3
    ) -> Optional[str]:
        """
        Get unified diff for a specific file.

        Args:
            relative_path: Relative path of file in snapshot
            context_lines: Number of context lines for diff

        Returns:
            Unified diff string, or None if file doesn't exist in both snapshots
        """
        file_a = self.snapshot_a / relative_path
        file_b = self.snapshot_b / relative_path

        if not file_a.exists() or not file_b.exists():
            return None

        try:
            with open(file_a, "r", encoding="utf-8", errors="replace") as f:
                lines_a = f.readlines()
            with open(file_b, "r", encoding="utf-8", errors="replace") as f:
                lines_b = f.readlines()

            # Generate unified diff
            diff = difflib.unified_diff(
                lines_a,
                lines_b,
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}",
                n=context_lines,
            )

            return "".join(diff)

        except Exception as e:
            logger.warning(f"Failed to diff file {relative_path}: {e}")
            return None

    def get_full_unified_diff(self, context_lines: int = 3) -> str:
        """
        Get unified diff for all changed files.

        Args:
            context_lines: Number of context lines

        Returns:
            Combined unified diff string
        """
        changed = self.get_changed_files()
        diff_parts = []

        # Modified files
        for file_path in changed["modified"]:
            file_diff = self.get_file_diff(file_path, context_lines)
            if file_diff:
                diff_parts.append(file_diff)

        # Added files
        for file_path in changed["added"]:
            diff_parts.append(f"New file: {file_path}\n")

        # Removed files
        for file_path in changed["removed"]:
            diff_parts.append(f"Deleted file: {file_path}\n")

        return "\n".join(diff_parts)

    def parse_file_content(self, file_path: Path) -> Dict[str, str]:
        """
        Parse a tab-delimited file into a dict (cell address -> value).

        Args:
            file_path: Path to file

        Returns:
            Dict mapping first column to second column
        """
        content = {}

        if not file_path.exists():
            return content

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    # Skip comments and headers
                    if line.startswith("#"):
                        continue

                    parts = line.rstrip("\n").split("\t", 1)
                    if len(parts) >= 2:
                        key, value = parts[0], parts[1]
                        content[key] = value

        except Exception as e:
            logger.warning(f"Failed to parse file {file_path}: {e}")

        return content

    def compare_tabular_file(
        self, relative_path: str
    ) -> Tuple[List[Tuple], List[Tuple], List[Tuple]]:
        """
        Compare a tab-delimited file (formulas, values, etc.).

        Args:
            relative_path: Relative path to file

        Returns:
            Tuple of (added, removed, modified) where each is a list of (key, value) tuples
        """
        file_a = self.snapshot_a / relative_path
        file_b = self.snapshot_b / relative_path

        content_a = self.parse_file_content(file_a)
        content_b = self.parse_file_content(file_b)

        keys_a = set(content_a.keys())
        keys_b = set(content_b.keys())

        added = [(k, content_b[k]) for k in sorted(keys_b - keys_a)]
        removed = [(k, content_a[k]) for k in sorted(keys_a - keys_b)]

        # Modified: same key, different value
        common_keys = keys_a & keys_b
        modified = [
            (k, content_a[k], content_b[k])
            for k in sorted(common_keys)
            if content_a[k] != content_b[k]
        ]

        return added, removed, modified
