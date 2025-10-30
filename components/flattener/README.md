# Excel Flattener

Convert Excel workbooks to deterministic, diff-friendly text representations.

## What It Does

Excel Flattener extracts everything from an Excel file into organised text files:

- **Formulas & Values**: Cell formulas and their literal values
- **VBA Macros**: Complete VBA code (even from password-protected projects)
- **Charts & Tables**: Chart definitions and Excel tables
- **Structure**: Sheet order, visibility, named ranges
- **Metadata**: Author, creation dates, workbook properties
- **Formats**: Cell formatting (fonts, colours, borders, alignment)

**Why?** Because Excel files are binary blobs that don't diff well. This tool produces deterministic, version-control-friendly text that lets you see exactly what changed.

## Features

- **Deterministic Output**: Same input always produces identical output (byte-for-byte)
- **Minimal Normalisation**: Extract data as-is from Excel with only essential normalisation
- **Multiple Formats**: Supports .xlsx, .xlsm, .xlsb, .xls
- **Configurable**: Environment-based configuration with sensible defaults
- **Standalone**: Can build single-file executable (no Python required)
- **Well-Logged**: Coloured console output with detailed file logging

---

## Quick Start

### Option 1: Run from Source (Development)

```bash
# Linux/Mac - launcher handles everything (venv, deps, run)
./scripts/run_flattener.sh flatten workbook.xlsx

# Windows
scripts\run_flattener.bat flatten workbook.xlsx
```

The launcher scripts automatically set up a virtual environment and install dependencies.

### Option 2: Run with Python

```bash
# Setup once
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r scripts/requirements.txt

# Flatten a workbook
python -m src flatten workbook.xlsx
```

### Option 3: Standalone Executable (Distribution)

```bash
# Build executable (creates dist/excel-flattener)
./scripts/build_package.sh  # Windows: scripts\build_package.bat

# Use executable (no Python required)
./dist/excel-flattener flatten workbook.xlsx
```

---

## Output Structure

The flattener creates a timestamped directory:

```
./tmp/flats/workbook-flat-20251030T143022Z-a3f5c8d1/
├── manifest.json              # Extraction metadata & file inventory
├── metadata.txt               # Workbook properties (author, dates)
├── workbook-structure.txt     # Sheet order, visibility, tab colours
├── named-ranges.txt           # Named ranges
├── tables.txt                 # Excel tables
├── autofilters.txt            # AutoFilter definitions
├── charts.txt                 # Chart definitions
├── vba/                       # VBA modules (if present)
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

**All files are always created** - even if empty (with headers + "(No X found)"), ensuring consistent structure for scripting and diffing.

---

## Usage Examples

### Basic Usage

```bash
# Flatten a workbook
python -m src flatten workbook.xlsx

# Include computed values (formula results)
python -m src flatten workbook.xlsx --include-computed

# Custom output directory
python -m src flatten workbook.xlsx -o ./my-output

# Debug logging
python -m src flatten workbook.xlsx --log-level DEBUG
```

### With Git Metadata

```bash
python -m src flatten workbook.xlsx \
  --origin-repo https://github.com/user/repo \
  --origin-commit abc123 \
  --origin-path data/workbook.xlsx \
  --origin-commit-message "Updated sales data"
```

This metadata gets recorded in `manifest.json` for traceability.

### View File Information

```bash
# Show file size, hash, validation status
python -m src info workbook.xlsx
```

### Show Current Configuration

```bash
# Display all environment variables and their values
python -m src config
```

### Get Help

```bash
python -m src --help
python -m src flatten --help
```

---

## Configuration

Configuration is managed through environment variables or a `.env` file.

### Quick Setup

```bash
# Copy template
cp .env.example .env

# Edit with your preferences
nano .env
```

### Environment Variables

All variables have the `FLATTENER_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLATTENER_OUTPUT_DIR` | `./tmp/flats` | Where to create flat outputs |
| `FLATTENER_LOG_DIR` | `./tmp/logs` | Where to write log files |
| `FLATTENER_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `FLATTENER_INCLUDE_COMPUTED` | `false` | Extract computed values (formula results)? |
| `FLATTENER_EXTRACTION_TIMEOUT` | `900` | Maximum extraction time (seconds) |
| `FLATTENER_MAX_FILE_SIZE_MB` | `200` | Maximum file size (MB) |
| `FLATTENER_TEMP_DIR` | `./tmp/temp` | Temporary file location |

### Example `.env`

```bash
FLATTENER_OUTPUT_DIR=./tmp/flats
FLATTENER_LOG_LEVEL=DEBUG
FLATTENER_INCLUDE_COMPUTED=true
FLATTENER_EXTRACTION_TIMEOUT=1200
```

### CLI Overrides

Command-line options override environment variables:

```bash
# Override output directory and log level
python -m src flatten workbook.xlsx -o ./output --log-level DEBUG

# Override timeout and max size
python -m src flatten workbook.xlsx --timeout 1800 --max-size 500
```

---

## Distribution

### Option 1: Source Distribution

Share the entire `flattener/` folder:

```bash
# Users run
./scripts/run_flattener.sh flatten workbook.xlsx
```

**Requirements**: Python 3.9+

### Option 2: Binary Distribution (Recommended)

Share just the `dist/` folder after building:

```bash
# Build
./scripts/build_package.sh

# Distribute dist/excel-flattener
# Users can run without Python installed
./excel-flattener flatten workbook.xlsx
```

**Requirements**: None (standalone executable)

**Note**: The `.env` file is NOT bundled. Users must create their own `.env` file in the same directory as the executable, or set environment variables.

---

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

---

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

---

## Troubleshooting

### "File too large"

Increase `FLATTENER_MAX_FILE_SIZE_MB`:

```bash
export FLATTENER_MAX_FILE_SIZE_MB=500
python -m src flatten large-workbook.xlsx
```

### "Extraction exceeded timeout"

Increase `FLATTENER_EXTRACTION_TIMEOUT`:

```bash
export FLATTENER_EXTRACTION_TIMEOUT=1800  # 30 minutes
python -m src flatten complex-workbook.xlsx
```

### Virtual Environment Issues

```bash
# Remove existing venv
rm -rf venv

# Recreate
python3 -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt
```

### Build Issues

```bash
# Clear PyInstaller cache
rm -rf build dist *.spec

# Rebuild
./scripts/build_package.sh
```

### Permission Errors (Linux/Mac)

```bash
# Make scripts executable
chmod +x scripts/run_flattener.sh scripts/build_package.sh
```

---

## Requirements

### For Running from Source

- Python 3.9 or higher
- pip (Python package manager)

### For Building Executable

- Python 3.9 or higher
- PyInstaller (installed by build scripts)

### Dependencies

All dependencies are in [scripts/requirements.txt](scripts/requirements.txt):

- **openpyxl** (≥3.1.0): Excel file parsing
- **lxml** (≥4.9.0): XML processing
- **oletools** (≥0.60): VBA extraction
- **click** (≥8.1.0): CLI framework
- **python-dotenv** (≥1.0.0): Environment configuration

---

## Folder Structure

```
flattener/
├── README.md              # This file (user guide)
├── .env.example           # Configuration template
├── src/                   # Production code (13 modules)
│   ├── __main__.py       # CLI entry point
│   ├── flattener.py      # Main orchestrator
│   └── ...               # Extraction modules
├── scripts/               # Build & development tools
│   ├── requirements.txt  # Python dependencies
│   ├── run_flattener.sh  # Development launcher (Linux/Mac)
│   ├── run_flattener.bat # Development launcher (Windows)
│   ├── build_package.sh  # Build script (Linux/Mac)
│   └── build_package.bat # Build script (Windows)
├── docs/                  # Developer documentation
│   └── DEVELOPER_GUIDE.md # Internal implementation guide
└── snippets/              # Development tools & examples
    ├── sample.xlsx        # Test Excel file
    ├── create_sample.py   # Sample file generator
    └── test_flattener.ipynb # Jupyter testing notebook
```

**For developers**: See [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for internal documentation.

---

## Logging

### Console Output

Coloured, user-friendly logs:

- 🟢 **INFO**: Progress updates
- 🟡 **WARNING**: Non-fatal issues
- 🔴 **ERROR**: Failures

```
[2025-10-30 14:30:22] INFO | flattener | Starting extraction: workbook.xlsx
[2025-10-30 14:30:23] INFO | flattener | ✓ File validated (15.3MB)
[2025-10-30 14:30:25] INFO | flattener | ✓ Workbook loaded (5 sheets)
```

### File Logging

Plain text logs written to `./tmp/logs/`:

- Always at DEBUG level (regardless of console level)
- Timestamped filenames: `flattener-20251030T143022.log`
- Full stack traces for errors

---

## Exit Codes

- `0`: Success
- `1`: Validation error (invalid file, too large, wrong format)
- `2`: Timeout (extraction exceeded `FLATTENER_EXTRACTION_TIMEOUT`)
- `3`: Extraction error (unexpected failure)

---

## Version

Current version: **2.1.0**

---

## Support

For developer documentation and internal implementation details, see [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md).
