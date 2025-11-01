#!/usr/bin/env python3
"""
Excel Differ - Main Entry Point

Make Excel files version-control friendly by converting them to text.

Commands:
  flatten  - Flatten a single Excel file to text representation
  diff     - Compare two Excel files and show differences
  workflow - Run a complete workflow (source → convert → flatten → destination)

Usage:
  python main.py flatten ./data/sample.xlsx
  python main.py diff ./data/sample.xlsx ./data/sample.xlsx
  python main.py workflow [config.yaml]
"""

import click

# Import registry and registration function
from src.registry import register_all_components

# Import CLI commands
from src.cli.flatten_command import flatten_command
from src.cli.diff_command import diff_command
from src.cli.workflow_command import workflow_command


@click.group()
@click.version_option(version='4.0.0', prog_name='Excel Differ')
def cli():
    """
    Excel Differ - Make Excel files version-control friendly

    Converts Excel workbooks into diff-friendly text representations,
    enabling meaningful version control and change tracking.

    \b
    Three main commands:
      flatten  - Flatten a single Excel file
      diff     - Compare two Excel files
      workflow - Run complete workflow (the main use case)

    \b
    Quick Start:
      1. Create input/ folder with Excel files
      2. Run: python main.py workflow
      3. Check output/ folder for results

    \b
    Examples:
      # Flatten one file
      python main.py flatten workbook.xlsx

      # Compare two versions
      python main.py diff old.xlsx new.xlsx

      # Run default workflow
      python main.py workflow

      # Run custom workflow
      python main.py workflow my-workflow.yaml
    """
    pass


# Add commands
cli.add_command(flatten_command)
cli.add_command(diff_command)
cli.add_command(workflow_command)


if __name__ == '__main__':
    # Register all components before running any commands
    # This ensures the registry knows about all available implementations
    register_all_components()

    # Run CLI
    cli()
