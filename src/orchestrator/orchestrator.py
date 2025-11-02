"""
Orchestrator - Coordinates the complete workflow

Orchestrates the Excel Differ workflow by coordinating:
1. Source - Get files
2. Converter - Convert if needed
3. Flattener - Flatten to text
4. Destination - Upload results
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
    ProcessingResult,
    SourceSyncState
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Workflow orchestrator.

    Coordinates source, converter, flattener, and destination components
    to process Excel files through the complete pipeline.
    """

    def __init__(
        self,
        source: SourceInterface,
        destination: DestinationInterface,
        converter: ConverterInterface,
        flattener: FlattenerInterface
    ):
        """
        Initialize orchestrator with all components.

        Args:
            source: Source component
            destination: Destination component
            converter: Converter component
            flattener: Flattener component
        """
        self.source = source
        self.destination = destination
        self.converter = converter
        self.flattener = flattener

    def run(self) -> WorkflowResult:
        """
        Run the complete workflow.

        Workflow steps:
        1. Get sync state from destination
        2. Get changed files from source
        3. For each file:
           a. Download from source
           b. Convert if needed
           c. Flatten
           d. Upload to destination
        4. Save new sync state

        Returns:
            WorkflowResult with statistics and any errors
        """
        processing_results = []
        errors = []

        try:
            # Step 1: Get sync state
            logger.info("Getting sync state...")
            sync_state = self.source.get_sync_state()
            logger.info(f"Last processed version: {sync_state.last_processed_version}")

            # Step 2: Get changed files
            logger.info("Getting changed files...")
            changed_files = self.source.get_changed_files(
                since_version=sync_state.last_processed_version,
            )

            logger.info(f"Found {len(changed_files)} file(s) to process")

            if not changed_files:
                logger.info("No files to process")
                return WorkflowResult(
                    files_processed=0,
                    files_succeeded=0,
                    files_failed=0,
                    processing_results=[],
                    errors=[]
                )

            # Step 3: Process each file
            for file_info in changed_files:
                result = self._process_file(file_info)
                processing_results.append(result)

            # Step 4: Save new sync state
            new_version = self.source.get_current_version()
            new_sync_state = SourceSyncState(
                last_processed_version=new_version,
                last_processed_date=file_info.version_date  # Use last file's date
            )
            self.destination.save_sync_state(new_sync_state)
            logger.info(f"Saved sync state: {new_version}")

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
