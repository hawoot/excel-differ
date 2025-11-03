"""
Orchestrator - Coordinates the complete workflow

Orchestrates the Excel Differ workflow by coordinating:
1. Source - Get files
2. Converter - Convert if needed
3. Flattener - Flatten to text
4. Destination - Upload results
5. StateManager - Per-file state tracking
"""

import logging
from pathlib import Path
from typing import Optional
import tempfile
import shutil

from src.interfaces import (
    SourceInterface,
    DestinationInterface,
    ConverterInterface,
    FlattenerInterface,
    WorkflowResult,
    ProcessingResult
)
from src.utils.state_manager import StateManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Workflow orchestrator.

    Coordinates source, converter, flattener, destination, and state manager
    to process Excel files through the complete pipeline with per-file state tracking.
    """

    def __init__(
        self,
        source: SourceInterface,
        destination: DestinationInterface,
        converter: ConverterInterface,
        flattener: FlattenerInterface,
        state_manager: StateManager
    ):
        """
        Initialize orchestrator with all components.

        Args:
            source: Source component
            destination: Destination component
            converter: Converter component
            flattener: Flattener component
            state_manager: StateManager for per-file state tracking
        """
        self.source = source
        self.destination = destination
        self.converter = converter
        self.flattener = flattener
        self.state_manager = state_manager

    def run(self) -> WorkflowResult:
        """
        Run the complete workflow with per-file state tracking.

        Workflow steps:
        1. Get changed files from source (using depth parameter for new files)
        2. For each file:
           a. Check if should process (based on per-file state)
           b. If yes:
              - Download from source
              - Convert if needed
              - Flatten
              - Upload to destination
              - Update file state immediately (success or failure)

        Returns:
            WorkflowResult with statistics and any errors
        """
        processing_results = []
        errors = []

        try:
            # Step 1: Get changed files from source
            # Note: source uses None for since_version (will use depth parameter)
            logger.info("Getting changed files from source...")
            changed_files = self.source.get_changed_files(since_version=None)

            logger.info(f"Found {len(changed_files)} file(s) from source")

            if not changed_files:
                logger.info("No files to process")
                return WorkflowResult(
                    files_processed=0,
                    files_succeeded=0,
                    files_failed=0,
                    processing_results=[],
                    errors=[]
                )

            # Step 2: Process each file (with per-file state checking)
            for file_info in changed_files:
                file_path = str(file_info.path)

                # Check if file should be processed based on state
                if not self.state_manager.should_process_file(file_path, file_info.version):
                    logger.info(f"Skipping {file_path} (already processed at version {file_info.version})")
                    continue

                # Process file
                result = self._process_file(file_info)
                processing_results.append(result)

                # Update state immediately after processing (per-file)
                error_msg = None if result.success else (result.errors[0] if result.errors else "Unknown error")
                self.state_manager.update_file_state(
                    file_path=file_path,
                    success=result.success,
                    version=file_info.version,
                    error=error_msg
                )

        except Exception as e:
            logger.error(f"Workflow failed: {e}", exc_info=True)
            errors.append(f"Workflow error: {str(e)}")

        # Calculate statistics
        files_processed = len(processing_results)
        files_succeeded = sum(1 for r in processing_results if r.success)
        files_failed = files_processed - files_succeeded

        return WorkflowResult(
            files_processed=files_processed,
            files_succeeded=files_succeeded,
            files_failed=files_failed,
            processing_results=processing_results,
            errors=errors
        )

    def _process_file(self, file_info) -> ProcessingResult:
        """
        Process a single file through the pipeline.

        Args:
            file_info: SourceFileInfo for the file to process

        Returns:
            ProcessingResult with success status
        """
        temp_dir = None

        try:
            # Create temporary directory for processing
            temp_dir = Path(tempfile.mkdtemp(prefix='excel-differ-'))

            logger.info(f"Processing: {file_info.path}")

            # Step 1: Download file
            download_path = temp_dir / file_info.path.name
            download_result = self.source.download_file(
                source_path=str(file_info.path),
                version=file_info.version,
                local_dest=download_path
            )

            if not download_result.success:
                logger.error(f"Download failed: {file_info.path}")
                return ProcessingResult(
                    success=False,
                    input_file=file_info.path,
                    conversion_result=None,
                    flatten_result=None,
                    errors=download_result.errors
                )

            # Step 2: Convert if needed
            current_file = download_path
            conversion_result = None

            if self.converter.needs_conversion(current_file):
                logger.info(f"Converting: {current_file.name}")
                conversion_result = self.converter.convert(
                    input_path=current_file,
                    output_dir=temp_dir
                )

                if not conversion_result.success:
                    logger.error(f"Conversion failed: {current_file.name}")
                    return ProcessingResult(
                        success=False,
                        input_file=file_info.path,
                        conversion_result=conversion_result,
                        flatten_result=None,
                        errors=conversion_result.errors
                    )

                if conversion_result.output_path:
                    current_file = conversion_result.output_path

            # Step 3: Flatten
            logger.info(f"Flattening: {current_file.name}")
            flatten_result = self.flattener.flatten(
                excel_file=current_file,
                origin=str(file_info.path),
            )

            if not flatten_result.success:
                logger.error(f"Flattening failed: {current_file.name}")
                return ProcessingResult(
                    success=False,
                    input_file=file_info.path,
                    conversion_result=conversion_result,
                    flatten_result=flatten_result,
                    errors=flatten_result.errors
                )

            # Step 4: Upload to destination
            if flatten_result.flat_root:
                logger.info(f"Uploading: {flatten_result.flat_root.name}")

                # Determine remote path (preserve source structure)
                remote_path = str(file_info.path.with_suffix('')) + '-flat'

                upload_result = self.destination.upload_directory(
                    local_dir=flatten_result.flat_root,
                    remote_path=remote_path,
                    message=f"Flattened {file_info.path}"
                )

                if not upload_result.success:
                    logger.error(f"Upload failed: {flatten_result.flat_root.name}")
                    return ProcessingResult(
                        success=False,
                        input_file=file_info.path,
                        conversion_result=conversion_result,
                        flatten_result=flatten_result,
                        errors=upload_result.errors
                    )

            logger.info(f"✓ Completed: {file_info.path}")
            return ProcessingResult(
                success=True,
                input_file=file_info.path,
                conversion_result=conversion_result,
                flatten_result=flatten_result,
                errors=[]
            )

        except Exception as e:
            logger.error(f"Processing failed for {file_info.path}: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                input_file=file_info.path,
                conversion_result=None,
                flatten_result=None,
                errors=[str(e)]
            )

        finally:
            # Cleanup temporary directory
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass  # Best effort cleanup
