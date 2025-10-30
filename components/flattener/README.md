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

### Option 1: Run from Source (Easiest for Development)

**Requirements**:
- Python 3.9+ installed
- Located in the `flattener/` directory
- Excel file to flatten (e.g., `workbook.xlsx`)

**Linux/Mac:**
```bash
cd /path/to/flattener/
./scripts/run_flattener.sh flatten workbook.xlsx
```

**Windows:**
```cmd
cd C:\path\to\flattener
scripts\run_flattener.bat flatten workbook.xlsx
```

**What the launcher scripts do:**
1. Check if `venv/` exists; if not, create it with `python3 -m venv venv`
2. Activate the virtual environment
3. Check if dependencies are installed; if not, run `pip install -r scripts/requirements.txt`
4. Load `.env` file if present
5. Run `python -m src <your-arguments>`
6. Deactivate virtual environment on exit

**First run** takes ~30 seconds to set up the environment. Subsequent runs are instant.

### Option 2: Run with Python Directly

**Requirements**:
- Python 3.9+ installed
- Located in the `flattener/` directory

```bash
# Setup once (manual)
cd /path/to/flattener/
python3 -m venv venv
source venv/bin/activate           # Linux/Mac
# OR
venv\Scripts\activate               # Windows

pip install -r scripts/requirements.txt

# Run the flattener
python -m src flatten workbook.xlsx

# When done (optional)
deactivate
```

**When to use this:**
- You want full control over the Python environment
- You're integrating into existing automation
- You're debugging or developing

### Option 3: Standalone Executable (Best for Distribution)

**Build Requirements**:
- Python 3.9+ with **shared library support** (`--enable-shared` flag when building Python)
- Located in the `flattener/` directory

**⚠️ Important**: PyInstaller requires Python built with shared libraries. Standard Python installations on Windows and Mac have this. Some Linux/Docker environments may not.

**To check if your Python supports PyInstaller:**
```bash
python3 -c "import sysconfig; print(sysconfig.get_config_var('Py_ENABLE_SHARED'))"
# Should output: 1 (supported) or 0 (not supported)
```

**Build the executable:**

**Linux/Mac:**
```bash
cd /path/to/flattener/
./scripts/build_package.sh
```

**Windows:**
```cmd
cd C:\path\to\flattener
scripts\build_package.bat
```

**What the build scripts do:**
1. Create `venv/` if it doesn't exist
2. Install dependencies from `scripts/requirements.txt`
3. Install PyInstaller
4. Clean previous builds (`dist/`, `build/`, `*.spec`)
5. Run PyInstaller with optimised settings:
   - `--onefile`: Single executable file
   - `--console`: Console application (not GUI)
   - `--hidden-import`: Include all required modules
   - `--collect-data`: Bundle openpyxl data files
6. Create executable in `dist/excel-flattener` (or `dist/excel-flattener.exe` on Windows)

**Build time**: ~2-5 minutes (first build), ~1-2 minutes (subsequent builds)

**Use the executable:**

```bash
# Linux/Mac
./dist/excel-flattener flatten workbook.xlsx

# Windows
dist\excel-flattener.exe flatten workbook.xlsx
```

**Distribute the executable:**
- Copy just the `dist/excel-flattener` (or `.exe`) file to any machine
- No Python installation required on target machine
- User can run it directly: `./excel-flattener flatten workbook.xlsx`
- User must create their own `.env` file if they want custom configuration (or use environment variables)

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

### Script Issues

#### "Permission denied" when running scripts (Linux/Mac)

Make scripts executable:

```bash
chmod +x scripts/run_flattener.sh scripts/build_package.sh
```

#### "python3: command not found"

Install Python 3.9+ or update the script to use your Python command:

```bash
# Check your Python version
python --version
python3 --version

# Edit PYTHON_CMD in the script if needed
# For example, change "python3" to "python"
```

#### Scripts don't find `src` module

**Must run scripts from the `flattener/` directory** (not from `scripts/`):

```bash
# ✓ Correct
cd /path/to/flattener/
./scripts/run_flattener.sh flatten workbook.xlsx

# ✗ Wrong
cd /path/to/flattener/scripts/
./run_flattener.sh flatten workbook.xlsx  # Will fail!
```

#### Virtual environment not activating on Windows

Use the correct activation command:

```cmd
REM Windows CMD
venv\Scripts\activate.bat

REM Windows PowerShell
venv\Scripts\Activate.ps1
```

If PowerShell gives execution policy errors:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Build Issues

#### "Python was built without a shared library"

Your Python installation doesn't support PyInstaller. Solutions:

1. **Install Python from python.org** (Windows/Mac) - includes shared libraries
2. **Use system package manager** (Linux):
   ```bash
   sudo apt-get install python3-dev  # Ubuntu/Debian
   sudo yum install python3-devel    # CentOS/RHEL
   ```
3. **Build Python from source with `--enable-shared`**:
   ```bash
   ./configure --enable-shared
   make
   sudo make install
   ```
4. **Use Docker with proper Python base image**:
   ```dockerfile
   FROM python:3.12-slim  # Has shared libraries
   ```

To verify your Python has shared library support:

```bash
python3 -c "import sysconfig; print(sysconfig.get_config_var('Py_ENABLE_SHARED'))"
# Should output: 1
```

#### Build succeeds but executable doesn't run

```bash
# Clear everything and rebuild
rm -rf venv build dist *.spec
./scripts/build_package.sh

# Test executable
./dist/excel-flattener --help
```

If it still fails, check the build log for missing modules and add them as `--hidden-import` in [build_package.sh](scripts/build_package.sh).

### Runtime Issues

#### "File too large"

Increase `FLATTENER_MAX_FILE_SIZE_MB`:

```bash
export FLATTENER_MAX_FILE_SIZE_MB=500
python -m src flatten large-workbook.xlsx
```

#### "Extraction exceeded timeout"

Increase `FLATTENER_EXTRACTION_TIMEOUT`:

```bash
export FLATTENER_EXTRACTION_TIMEOUT=1800  # 30 minutes
python -m src flatten complex-workbook.xlsx
```

#### Logs not appearing in ./tmp/logs/

Check that:
1. You're running from the `flattener/` directory
2. The directory has write permissions
3. `FLATTENER_LOG_DIR` is not set to a different location

```bash
# Check current config
python -m src config

# Explicitly set log directory
export FLATTENER_LOG_DIR=./tmp/logs
python -m src flatten workbook.xlsx

# Check logs
ls -la ./tmp/logs/
```

#### "Module not found" errors

Dependencies not installed:

```bash
# With launcher scripts (automatic)
./scripts/run_flattener.sh flatten workbook.xlsx

# Manual installation
pip install -r scripts/requirements.txt
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
