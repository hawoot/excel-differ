"""
Workflow Command - Run Excel Differ workflow

Executes a complete workflow: source → convert → flatten → destination
"""

import sys
from pathlib import Path
import click

from src.workflows.loader import load_workflow


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

    # Load workflow
    try:
        workflow = load_workflow(config_file)
    except Exception as e:
        click.echo(f"\n✗ Failed to load workflow: {e}", err=True)
        sys.exit(1)

    # Display workflow info
    click.echo(f"\nWorkflow Configuration:")
    click.echo(f"  Source: {workflow.source.implementation}")
    click.echo(f"  Destination: {workflow.destination.implementation}")
    click.echo(f"  Converter: {workflow.converter.implementation}")
    click.echo(f"  Flattener: {workflow.flattener.implementation}")
    click.echo()

    # TODO: Create and run orchestrator
    # For now, just show that the workflow loaded successfully
    click.echo("✓ Workflow loaded successfully!")
    click.echo()
    click.echo("NOTE: Orchestrator not yet implemented.")
    click.echo("      This will be completed in the next phase.")
    click.echo()
    click.echo("To implement:")
    click.echo("  1. Create Orchestrator class")
    click.echo("  2. Implement source/destination components")
    click.echo("  3. Wire everything together")

    sys.exit(0)

    # Future implementation:
    # from src.orchestrator import Orchestrator
    # from src.registry import registry
    #
    # # Create component instances
    # source = registry.create_source(workflow.source.implementation, workflow.source.config)
    # destination = registry.create_destination(workflow.destination.implementation, workflow.destination.config)
    # converter = registry.create_converter(workflow.converter.implementation, workflow.converter.config)
    # flattener = registry.create_flattener(workflow.flattener.implementation, workflow.flattener.config)
    #
    # # Create and run orchestrator
    # orchestrator = Orchestrator(source, destination, converter, flattener, workflow)
    # result = orchestrator.run()
    #
    # # Display results
    # click.echo(f"\n✓ Workflow complete!")
    # click.echo(f"  Files processed: {result.files_processed}")
    # click.echo(f"  Files succeeded: {result.files_succeeded}")
    # click.echo(f"  Files failed: {result.files_failed}")
