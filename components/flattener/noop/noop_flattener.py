"""
NoOp Flattener - Explicit no-flattening implementation

Acts as a file copier when flattening is not needed.
"""

from pathlib import Path
from typing import Optional
import shutil

from components.core.interfaces import FlattenerInterface, FlattenResult


class NoOpFlattener(FlattenerInterface):
    """
    Explicit no-operation flattener.

    Use in converter-only workflows where you just want to copy
    the file (or converted file) without flattening.

    Acts as a file copier - creates a simple directory with the original file.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.output_dir = Path(config.get('output_dir', './tmp/noop-flattener'))

    def flatten(
        self,
        excel_file: Path,
        origin_repo: Optional[str] = None,
        origin_path: Optional[str] = None,
        origin_commit: Optional[str] = None
    ) -> FlattenResult:
        """
        "Flatten" by copying file to output directory.

        Creates a directory with timestamp and copies the file as-is.
        """
        from datetime import datetime

        # Create timestamped output directory
        timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        flat_root = self.output_dir / f"{excel_file.stem}-copy-{timestamp}"
        flat_root.mkdir(parents=True, exist_ok=True)

        # Copy file
        dest_file = flat_root / excel_file.name
        shutil.copy2(excel_file, dest_file)

        return FlattenResult(
            success=True,
            input_path=excel_file,
            flat_root=flat_root,
            manifest_path=None,  # No manifest for NoOp
            warnings=[f"NoOpFlattener: File copied as-is to {flat_root}"],
            errors=[]
        )

    def get_name(self) -> str:
        return "NoOpFlattener"
