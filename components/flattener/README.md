# Excel Flattener

Convert Excel workbooks to deterministic, diff-friendly text representations.

## Features

- **Complete Extraction**: Formulas, values, VBA macros, charts, tables, named ranges, formats
- **Minimal Normalisation**: Extract data as-is from Excel with only essential normalisation
- **Deterministic Output**: Same input always produces identical output (byte-for-byte)
- **VBA Support**: Extract VBA code, including from password-protected projects
- **Multiple Formats**: Supports .xlsx, .xlsm, .xlsb, .xls
- **Configurable**: Environment-based configuration with sensible defaults
- **Standalone**: Single-file executable available (PyInstaller)
- **Well-Logged**: Colored console output with detailed file logging

## Quick Start

### Using Python

```bash
# Setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Flatten a workbook
python -m src flatten workbook.xlsx
```

### Using Launcher Scripts

```bash
# Linux/Mac
./scripts/run_flattener.sh flatten workbook.xlsx

# Windows
scripts\run_flattener.bat flatten workbook.xlsx
```

The launcher scripts automatically set up the virtual environment and install dependencies.

### Using Standalone Executable

```bash
# Build executable
./scripts/build_package.sh  # On Windows: scripts\build_package.bat

# Use executable
./dist/excel-flattener flatten workbook.xlsx
```

## Installation

### Requirements

- Python 3.9 or higher
- pip (Python package manager)

### Dependencies

All dependencies are listed in [requirements.txt](requirements.txt):

- **openpyxl** (≥3.1.0): Excel file parsing
- **lxml** (≥4.9.0): XML processing
- **oletools** (≥0.60): VBA extraction
- **click** (≥8.1.0): CLI framework
- **python-dotenv** (≥1.0.0): Environment configuration

## Configuration

Configuration is managed through environment variables or a `.env` file.

### Environment Variables

All variables have the `FLATTENER_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLATTENER_OUTPUT_DIR` | `./flats` | Where to create flat outputs |
| `FLATTENER_LOG_DIR` | *(system temp)* | Where to write log files |
| `FLATTENER_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `FLATTENER_INCLUDE_COMPUTED` | `false` | Extract computed values? |
| `FLATTENER_EXTRACTION_TIMEOUT` | `900` | Maximum extraction time (seconds) |
| `FLATTENER_MAX_FILE_SIZE_MB` | `200` | Maximum file size (MB) |
| `FLATTENER_TEMP_DIR` | *(system temp)* | Temporary file location |

### Creating a .env File

Copy the example and customise:

```bash
cp .env.example .env
# Edit .env with your preferences
```

Example `.env`:

```bash
FLATTENER_OUTPUT_DIR=./my-flats
FLATTENER_LOG_LEVEL=DEBUG
FLATTENER_INCLUDE_COMPUTED=true
FLATTENER_EXTRACTION_TIMEOUT=1200
```

## Usage

### Command-Line Interface

#### Flatten a Workbook

```bash
# Basic usage
python -m src flatten workbook.xlsx

# With options
python -m src flatten workbook.xlsx --include-computed --log-level DEBUG

# Custom output directory
python -m src flatten workbook.xlsx -o ./output

# With git origin metadata
python -m src flatten workbook.xlsx \
  --origin-repo https://github.com/user/repo \
  --origin-commit abc123 \
  --origin-path data/workbook.xlsx
```

#### View Configuration

```bash
python -m src config
```

#### File Information

```bash
python -m src info workbook.xlsx
```

#### Help

```bash
python -m src --help
python -m src flatten --help
```

### Programmatic Usage

```python
from pathlib import Path
from src import Flattener, setup_logging

# Setup logging
setup_logging(log_level='INFO', log_dir=None, component='flattener')

# Create flattener
flattener = Flattener(
    output_dir=Path('./flats'),
    include_computed=False,
    timeout=900,
    max_file_size_mb=200
)

# Flatten workbook
flat_root = flattener.flatten(
    excel_file=Path('workbook.xlsx'),
    origin_repo='https://github.com/user/repo',
    origin_commit='abc123'
)

print(f"Flattened to: {flat_root}")
```

## Output Structure

The flattener creates a timestamped directory with the following structure:

```
workbook-flat-2025-10-30T14-30-22Z-a1b2c3d4/
├── manifest.json              # Extraction metadata and file inventory
├── metadata.txt               # Workbook properties (author, dates, etc.)
├── structure.txt              # Sheet order, visibility, tab colours
├── named-ranges.txt           # Named ranges and constants
├── tables.txt                 # Excel tables (ListObjects)
├── autofilters.txt            # AutoFilter definitions
├── charts.txt                 # Chart definitions and series
├── vba/                       # VBA macros (if present)
│   ├── vba-summary.txt
│   ├── Module1.vba
│   └── ThisWorkbook.vba
└── sheets/                    # Per-sheet data
    ├── Sheet1/
    │   ├── formulas.txt       # Cell formulas
    │   ├── literal-values.txt # Hardcoded values
    │   ├── computed-values.txt# Formula results (optional)
    │   └── formats.txt        # Cell formatting
    └── Sheet2/
        └── ...
```

### Output Files

#### manifest.json

JSON file tracking:
- Original file hash (SHA256)
- Extraction timestamp
- Extractor version
- All sheets with indices and visibility
- All generated files with hashes
- Warnings encountered
- Git origin metadata (if provided)

#### metadata.txt

Workbook properties:
- Author
- Created/Modified dates
- Title, Subject, Description
- Company, Version
- Calculation mode
- Excel version

#### structure.txt

Sheet information:
- Index (1-based position)
- Name
- Visibility (visible/hidden/veryHidden)
- Tab colour
- Row/column counts

#### formulas.txt

Cell formulas in row-major order:

```
A1: =SUM(B1:B10)
A2: =AVERAGE(C1:C10)
B5: =IF(A5>10, "High", "Low")
```

#### literal-values.txt

Hardcoded cell values:

```
A1: 42 (number)
A2: Hello World (text)
A3: 2025-10-30T00:00:00Z (date)
A4: TRUE (boolean)
```

#### computed-values.txt

Formula results (only if `FLATTENER_INCLUDE_COMPUTED=true`):

```
A1: 450 (number)
A2: 45.5 (number)
B5: High (text)
```

#### formats.txt

Cell formatting (fonts, fills, borders, alignment):

```
A1:
  number_format: 0.00
  font:
    name: Arial
    size: 12
    bold: true
    colour: FF0000
  fill:
    type: solid
    colour: FFFF00
```

## Normalisation Philosophy

The flattener extracts data **as-is** from Excel with minimal normalisation:

### What is NOT normalised

- **Formulas**: Preserved exactly as stored (case, spacing, structure)
- **Numbers**: Full precision, no rounding or truncation
- **Text**: Preserved verbatim
- **Case**: No case changes to formulas or cell references

### What IS normalised

- **Text Encoding**: UTF-8
- **Line Endings**: LF (`\n`)
- **Cell Order**: Row-major sorting (A1, A2, B1, B2, ...)

This ensures meaningful diffs while maintaining data fidelity.

## Supported Excel Features

### Always Extracted

- ✓ Formulas (including array formulas and dynamic arrays)
- ✓ Literal values (numbers, text, booleans, dates, errors)
- ✓ VBA macros (including password-protected)
- ✓ Charts (all types with series and axes)
- ✓ Tables (Excel tables/ListObjects)
- ✓ AutoFilters
- ✓ Named ranges (workbook and worksheet scope)
- ✓ Cell formats (fonts, fills, borders, alignment, number formats)
- ✓ Metadata (author, dates, properties)
- ✓ Sheet structure (order, visibility, tab colours)

### Optional

- ⚙ Computed values (formula results) - controlled by `FLATTENER_INCLUDE_COMPUTED`

### Not Extracted

- ✗ Images (photos, logos)
- ✗ Embedded objects (OLE objects)
- ✗ Comments/notes
- ✗ Sparklines
- ✗ Slicers
- ✗ Pivot tables

## Building Standalone Executable

### Linux/Mac

```bash
./build_package.sh
```

### Windows

```cmd
build_package.bat
```

The build creates a single-file executable in the `dist/` directory:

- **Portable**: No Python installation required
- **Self-contained**: All dependencies bundled
- **Slower startup**: Extracts to temp on first run (~2-3 seconds)

### Distribution

The executable can be distributed as-is:

```bash
# Copy to destination
cp dist/excel-flattener /usr/local/bin/

# Use anywhere
excel-flattener flatten workbook.xlsx
```

**Note**: The `.env` file is NOT bundled. Users must create their own `.env` file in the same directory as the executable, or set environment variables.

## Logging

### Console Output

Colored, user-friendly logs:

- 🟢 **INFO**: Progress updates
- 🟡 **WARNING**: Non-fatal issues
- 🔴 **ERROR**: Failures

Example:

```
[2025-10-30 14:30:22] INFO | flattener | ======================================================================
[2025-10-30 14:30:22] INFO | flattener | Starting extraction: workbook.xlsx
[2025-10-30 14:30:22] INFO | flattener | ======================================================================
[2025-10-30 14:30:23] INFO | flattener | ✓ File validated (15.3MB)
[2025-10-30 14:30:25] INFO | flattener | ✓ Workbook loaded (5 sheets)
```

### File Logging

Plain text logs written to `FLATTENER_LOG_DIR` (or system temp):

- Always at DEBUG level (regardless of console level)
- Timestamped filenames: `flattener-2025-10-30T14-30-22.log`
- Full stack traces for errors
- Rotated automatically (not implemented - future enhancement)

## Error Handling

### Exit Codes

- `0`: Success
- `1`: Validation error (invalid file, too large, wrong format)
- `2`: Timeout (extraction exceeded `FLATTENER_EXTRACTION_TIMEOUT`)
- `3`: Extraction error (unexpected failure)

### Common Issues

#### "File too large"

Increase `FLATTENER_MAX_FILE_SIZE_MB`:

```bash
export FLATTENER_MAX_FILE_SIZE_MB=500
```

#### "Extraction exceeded timeout"

Increase `FLATTENER_EXTRACTION_TIMEOUT`:

```bash
export FLATTENER_EXTRACTION_TIMEOUT=1800  # 30 minutes
```

#### "oletools not available"

VBA extraction requires oletools:

```bash
pip install oletools
```

## Development

### Project Structure

```
flattener/
├── src/                       # Core library
│   ├── __init__.py           # Package exports
│   ├── __main__.py           # CLI interface (Click)
│   ├── flattener.py          # Main Flattener class
│   ├── utils.py              # Logging, hashing, config
│   ├── manifest.py           # Manifest generation
│   ├── normalizer.py         # Normalisation utilities
│   ├── metadata.py           # Workbook metadata
│   ├── structure.py          # Sheet structure
│   ├── sheets.py             # Sheet data extraction
│   ├── vba.py                # VBA extraction
│   ├── tables.py             # Tables and autofilters
│   ├── charts.py             # Chart extraction
│   └── named_ranges.py       # Named ranges
├── scripts/                   # Scripts
│   ├── run_flattener.sh      # Launcher (Linux/Mac)
│   ├── run_flattener.bat     # Launcher (Windows)
│   ├── build_package.sh      # Build script (Linux/Mac)
│   ├── build_package.bat     # Build script (Windows)
│   └── create_sample.py      # Sample file generator
├── requirements.txt           # Python dependencies
├── .env.example              # Configuration template
├── test_flattener.ipynb      # Jupyter notebook
├── README.md                 # Documentation
└── IMPLEMENTATION_STATUS.md  # Implementation status
```

### Running Tests

Tests to be implemented in future version.

### Code Style

- **Language**: British English in all documentation and user-facing text
- **Docstrings**: Google-style
- **Formatting**: Follow PEP 8
- **Type Hints**: Used where beneficial

## Troubleshooting

### Virtual Environment Issues

If you encounter venv issues:

```bash
# Remove existing venv
rm -rf venv

# Recreate
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### PyInstaller Issues

If build fails:

```bash
# Clear PyInstaller cache
rm -rf build dist *.spec

# Rebuild with verbose output
pyinstaller --onefile --name excel-flattener --log-level DEBUG cli.py
```

### Permission Errors

On Linux/Mac, ensure scripts are executable:

```bash
chmod +x scripts/run_flattener.sh scripts/build_package.sh
```

## Version

Current version: **2.1.0**

## Licence

To be determined.

## Support

For issues and feature requests, please contact the development team.
