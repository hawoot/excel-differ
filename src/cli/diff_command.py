"""
Diff Command - Compare two Excel files

On-demand diff that flattens two files and compares them.
"""

import sys
from pathlib import Path
import click

from src.registry import registry
from src.differ import Differ, JSONFormatter


@click.command('diff')
@click.argument('file1', type=click.Path(exists=True, path_type=Path))
@click.argument('file2', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output file for diff results (default: print to console)'
)
@click.option(
    '--format',
    type=click.Choice(['json'], case_sensitive=False),
    default='json',
    help='Output format (default: json, html: coming soon)'
)
def diff_command(file1, file2, output, format):
    """
    Compare two Excel files.

    FILE1: Path to first Excel file
    FILE2: Path to second Excel file

    Flattens both files and produces a structured diff showing:
    - Files that differ
    - Lines added/removed
    - Files only in one version

    \b
    Examples:
      # Compare two files (output to console)
      python main.py diff file1.xlsx file2.xlsx

      # Save diff to JSON file
      python main.py diff file1.xlsx file2.xlsx -o diff-result.json

      # Compare and see results
      python main.py diff old-version.xlsx new-version.xlsx
    """
    # Create flattener for diffing
    flattener_config = {
        'output_dir': './tmp/diff-flats',
        'include_computed': False,
        'include_literal': True,
        'include_formats': True,
        'timeout': 900,
        'max_file_size_mb': 200
    }

    try:
        flattener = registry.create_flattener('openpyxl', flattener_config)
    except ValueError as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        click.echo("  Make sure components are registered.", err=True)
        sys.exit(1)

    # Create differ
    differ = Differ(flattener)

    # Perform diff
    click.echo(f"\nComparing {file1.name} and {file2.name}...")
    click.echo("  Step 1/3: Flattening first file...")

    diff_result = differ.diff_files(file1, file2, output_format=format)

    if not diff_result['success']:
        click.echo(f"\n✗ Diff failed:", err=True)
        for error in diff_result.get('errors', []):
            click.echo(f"  - {error}", err=True)
        sys.exit(1)

    # Format output
    formatter = JSONFormatter()

    if output:
        # Save to file
        formatter.save(diff_result, str(output), pretty=True)
        click.echo(f"\n✓ Diff complete!")
        click.echo(f"  Results saved to: {output}")
    else:
        # Print to console
        json_output = formatter.format(diff_result, pretty=True)
        click.echo("\n" + "=" * 60)
        click.echo("DIFF RESULTS")
        click.echo("=" * 60)
        click.echo(json_output)
        click.echo("=" * 60)

    # Print summary
    click.echo(f"\nSummary:")
    click.echo(f"  Files compared: {diff_result['files_compared']}")
    click.echo(f"  Files different: {diff_result['files_different']}")
    if diff_result['files_only_in_file1']:
        click.echo(f"  Only in {file1.name}: {len(diff_result['files_only_in_file1'])}")
    if diff_result['files_only_in_file2']:
        click.echo(f"  Only in {file2.name}: {len(diff_result['files_only_in_file2'])}")

    sys.exit(0)
