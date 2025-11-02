"""
Workflow Command - Run Excel Differ workflow

Executes a complete workflow: source → convert → flatten → destination
"""

import os
import sys
from pathlib import Path
import click

from src.utils.logging_setup import setup_logging


@click.command('workflow')
@click.argument(
    'config_file',
    type=click.Path(exists=True, path_type=Path),
    required=False
)
def workflow_command(config_file):
    """
    Run Excel Differ workflow.

    CONFIG_FILE: Path to workflow YAML config (optional)

    If no config file is specified, uses: workflow_definitions/default.yaml

    The workflow coordinates:
    - Source: Get Excel files (from Bitbucket, local folder, etc.)
    - Converter: Convert formats if needed (.xlsb → .xlsm)
    - Flattener: Flatten to text representation
    - Destination: Upload results (to Bitbucket, local folder, etc.)

    \b
    Examples:
      # Run with default workflow
      python main.py workflow

      # Run with specific config
      python main.py workflow workflow_definitions/templates/bitbucket-to-local.yaml

      # Run with custom config
      python main.py workflow /path/to/my-workflow.yaml
    """
    # Determine config file
    if not config_file:
        config_file = Path('workflow_definitions/default.yaml')
        click.echo(f"Using default workflow: {config_file}")

    # Check if file exists
    if not config_file.exists():
        click.echo(f"\n✗ Config file not found: {config_file}", err=True)
        if not config_file.is_absolute():
            click.echo(f"  Looking in: {config_file.absolute()}", err=True)
        sys.exit(1)

    # Create orchestrator from config
    from src.orchestrator.factory import create_orchestrator_from_config

    try:
        click.echo("Creating components...")
        orchestrator, workflow = create_orchestrator_from_config(config_file)

        # Initialize logging from workflow config
        log_level = os.getenv('EXCEL_DIFFER_LOG_LEVEL', 'INFO').upper()
        setup_logging(
            log_level=log_level,
            log_dir=workflow.logging.log_dir,
            component='excel-differ-workflow-command'
        )

        # Display workflow info
        click.echo(f"\nWorkflow Configuration:")
        click.echo(f"  Source: {workflow.source.implementation}")
        click.echo(f"  Destination: {workflow.destination.implementation}")
        click.echo(f"  Converter: {workflow.converter.implementation}")
        click.echo(f"  Flattener: {workflow.flattener.implementation}")
        click.echo(f"  Log dir: {workflow.logging.log_dir}")
        click.echo()

        # Run orchestrator
        click.echo("Running workflow...\n")
        result = orchestrator.run()

        # Display results
        click.echo(f"\n{'='*60}")
        click.echo(f"✓ Workflow complete!")
        click.echo(f"{'='*60}")
        click.echo(f"  Files processed: {result.files_processed}")
        click.echo(f"  Files succeeded: {result.files_succeeded}")
        click.echo(f"  Files failed: {result.files_failed}")

        if result.errors:
            click.echo(f"\n  Errors:")
            for error in result.errors:
                click.echo(f"    - {error}")

        # Show details for failed files
        if result.files_failed > 0:
            click.echo(f"\n  Failed files:")
            for proc_result in result.processing_results:
                if not proc_result.success:
                    click.echo(f"    - {proc_result.input_file}")
                    for error in proc_result.errors:
                        click.echo(f"        {error}")

        sys.exit(0 if result.files_failed == 0 else 1)

    except Exception as e:
        click.echo(f"\n✗ Workflow failed: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
