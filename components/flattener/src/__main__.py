"""
Command-line interface for Excel Flattener.

Provides a user-friendly CLI using Click.
"""
import sys
from pathlib import Path

import click

from . import Flattener, TimeoutError, load_config, setup_logging


@click.group()
@click.version_option(version='2.1.0', prog_name='Excel Flattener')
def cli():
    """
    Excel Flattener - Convert Excel workbooks to diff-friendly text.

    Extract formulas, values, VBA, charts, and more from Excel files
    into a deterministic, version-control-friendly format.
    """
    pass


@cli.command()
@click.argument('excel_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--output-dir', '-o',
    type=click.Path(path_type=Path),
    help='Output directory for flat files (default: ./tmp/flats)'
)
@click.option(
    '--include-computed/--no-computed',
    default=None,
    help='Include computed values / formula results (default: False)'
)
@click.option(
    '--include-literal/--no-literal',
    default=None,
    help='Include literal values / hardcoded values (default: True)'
)
@click.option(
    '--include-formats/--no-formats',
    default=None,
    help='Include cell formatting (default: True)'
)
@click.option(
    '--origin-repo',
    help='Git repository URL (for traceability in manifest)'
)
@click.option(
    '--origin-path',
    help='Path in repository (for traceability in manifest)'
)
@click.option(
    '--origin-commit',
    help='Git commit SHA (for traceability in manifest)'
)
@click.option(
    '--origin-commit-message',
    help='Git commit message (for traceability in manifest)'
)
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
    help='Logging level (default: INFO)'
)
@click.option(
    '--timeout',
    type=int,
    help='Extraction timeout in seconds (default: 900)'
)
@click.option(
    '--max-size',
    type=int,
    help='Maximum file size in MB (default: 200)'
)
def flatten(
    excel_file,
    output_dir,
    include_computed,
    include_literal,
    include_formats,
    origin_repo,
    origin_path,
    origin_commit,
    origin_commit_message,
    log_level,
    timeout,
    max_size
):
    """
    Flatten an Excel workbook to text files.

    EXCEL_FILE: Path to Excel file (.xlsx, .xlsm, .xlsb, .xls)

    \b
    Examples:
      # Basic usage (extracts formulas + literal values + formats)
      flatten workbook.xlsx

      # Include computed values (formula results)
      flatten workbook.xlsx --include-computed

      # Only formulas and computed values (no literal values or formats)
      flatten workbook.xlsx --include-computed --no-literal --no-formats

      # Custom output directory with debug logging
      flatten workbook.xlsx -o ./output --log-level DEBUG

      # With git traceability metadata
      flatten workbook.xlsx --origin-repo https://github.com/user/repo --origin-commit abc123
    """
    # Load configuration
    config = load_config()

    # Override with CLI arguments (use config defaults for None values)
    output_dir = output_dir or Path(config['output_dir'])
    include_computed = include_computed if include_computed is not None else False
    include_literal = include_literal if include_literal is not None else True
    include_formats = include_formats if include_formats is not None else True
    log_level = log_level or config['log_level']
    timeout = timeout if timeout is not None else config['extraction_timeout']
    max_size = max_size if max_size is not None else config['max_file_size_mb']
    log_dir = config['log_dir']

    # Setup logging
    setup_logging(log_level, log_dir, component='flattener')

    # Create flattener
    flattener = Flattener(
        output_dir=output_dir,
        include_computed=include_computed,
        include_literal=include_literal,
        include_formats=include_formats,
        timeout=timeout,
        max_file_size_mb=max_size
    )

    # Flatten workbook
    try:
        flat_root = flattener.flatten(
            excel_file=excel_file,
            origin_repo=origin_repo,
            origin_path=origin_path,
            origin_commit=origin_commit,
            origin_commit_message=origin_commit_message
        )

        click.echo(f"\n✓ Flattening complete!")
        click.echo(f"  Output: {flat_root}")
        sys.exit(0)

    except ValueError as e:
        click.echo(f"\n✗ Validation error: {e}", err=True)
        sys.exit(1)

    except TimeoutError as e:
        click.echo(f"\n✗ Timeout: {e}", err=True)
        sys.exit(2)

    except Exception as e:
        click.echo(f"\n✗ Extraction failed: {e}", err=True)
        sys.exit(3)


@cli.command()
def config():
    """
    Show current configuration.

    Displays all environment variables and their values.
    """
    config_dict = load_config()

    click.echo("\nCurrent Configuration:")
    click.echo("=" * 50)

    for key, value in config_dict.items():
        # Format key nicely
        display_key = key.replace('_', ' ').title()
        click.echo(f"  {display_key}: {value}")

    click.echo()


@cli.command()
@click.argument('excel_file', type=click.Path(exists=True, path_type=Path))
def info(excel_file):
    """
    Display information about an Excel file.

    EXCEL_FILE: Path to Excel file

    Shows file size, hash, and basic validation.
    """
    from .utils import get_file_hash

    file_path = Path(excel_file)

    click.echo(f"\nFile Information:")
    click.echo("=" * 50)
    click.echo(f"  Name: {file_path.name}")
    click.echo(f"  Path: {file_path.absolute()}")

    # Size
    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    click.echo(f"  Size: {size_mb:.2f} MB ({size_bytes:,} bytes)")

    # Hash
    click.echo(f"  SHA256: Computing...", nl=False)
    file_hash = get_file_hash(file_path)
    click.echo(f"\r  SHA256: {file_hash}")

    # Extension
    click.echo(f"  Extension: {file_path.suffix}")

    # Validation
    valid_extensions = ['.xlsx', '.xlsm', '.xlsb', '.xls']
    is_valid = file_path.suffix.lower() in valid_extensions

    if is_valid:
        click.echo(f"  Status: ✓ Valid Excel file")
    else:
        click.echo(f"  Status: ✗ Unsupported format (supported: {', '.join(valid_extensions)})")

    click.echo()


if __name__ == '__main__':
    cli()
