"""
Flatten Command - Flatten a single Excel file

Extracts a standalone Excel file to text representation.
"""

import os
import sys
from pathlib import Path
import click

from src.registry import registry
from src.utils.logging_setup import setup_logging


@click.command('flatten')
@click.argument('excel_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--output-dir', '-o',
    type=click.Path(path_type=Path),
    help='Output directory for flat files (default: ./tmp/flats)'
)
@click.option(
    '--include-computed/--no-computed',
    default=False,
    help='Include computed values / formula results (default: False)'
)
@click.option(
    '--include-literal/--no-literal',
    default=True,
    help='Include literal values / hardcoded values (default: True)'
)
@click.option(
    '--include-formats/--no-formats',
    default=True,
    help='Include cell formatting (default: True)'
)
def flatten_command(
    excel_file,
    output_dir,
    include_computed,
    include_literal,
    include_formats
):
    """
    Flatten an Excel workbook to text files.

    EXCEL_FILE: Path to Excel file (.xlsx, .xlsm, .xlsb, .xls)

    \b
    Examples:
      # Basic usage (extracts formulas + literal values + formats)
      python main.py flatten workbook.xlsx

      # Include computed values (formula results)
      python main.py flatten workbook.xlsx --include-computed

      # Only formulas (no literal values or formats)
      python main.py flatten workbook.xlsx --no-literal --no-formats

      # Custom output directory
      python main.py flatten workbook.xlsx -o ./output
    """
    # Initialize logging
    log_level = os.getenv('EXCEL_DIFFER_LOG_LEVEL', 'INFO').upper()
    setup_logging(log_level=log_level, log_dir='./logs', component='excel-differ-flatten-command')

    # Prepare flattener config
    flattener_config = {
        'output_dir': str(output_dir) if output_dir else './tmp/flats',
        'include_computed': include_computed,
        'include_literal': include_literal,
        'include_formats': include_formats,
        'timeout': 900,
        'max_file_size_mb': 200
    }

    # Create flattener using registry
    try:
        flattener = registry.create_flattener('openpyxl', flattener_config)
    except ValueError as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        click.echo("  Make sure components are registered (call register_all_components()).", err=True)
        sys.exit(1)

    # Flatten workbook
    try:
        result = flattener.flatten(excel_file)

        if result.success:
            click.echo(f"\n✓ Flattening complete!")
            click.echo(f"  Input: {result.input_path}")
            click.echo(f"  Output: {result.flat_root}")
            if result.manifest_path:
                click.echo(f"  Manifest: {result.manifest_path}")
            sys.exit(0)
        else:
            click.echo(f"\n✗ Flattening failed:", err=True)
            for error in result.errors:
                click.echo(f"  - {error}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n✗ Unexpected error: {e}", err=True)
        sys.exit(3)
