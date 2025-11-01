# Excel Flattener - Developer Guide

**Internal documentation for developers working on the flattener.**

---

## Table of Contents

1. [Folder Structure](#folder-structure)
2. [How It Works](#how-it-works)
3. [Module Reference](#module-reference)
4. [Adding Features](#adding-features)
5. [Build & Distribution](#build--distribution)
6. [Configuration](#configuration)
7. [Testing](#testing)

---

## Folder Structure

### Overview

```
flattener/
├── README.md              User-facing documentation
├── .env.example           Configuration template
├── src/                   Production code
├── scripts/               Build & development tools
├── docs/                  This file (developer guide)
└── snippets/              Development tools & examples
```

### Directories

**`src/`** - Production source code (13 modules)
- `__main__.py` - CLI entry point (Click framework)
- `flattener.py` - Main orchestrator, coordinates all extraction
- Module names match their output files (see below)

**`scripts/`** - Build and development tools
- `requirements.txt` - Python dependencies (used by run/build scripts)
- `run_flattener.sh/.bat` - Development launchers (auto-setup venv)
- `build_package.sh/.bat` - PyInstaller build scripts

**`docs/`** - Documentation
- `DEVELOPER_GUIDE.md` - This file

**`snippets/`** - Development tools
- `sample.xlsx` - Test Excel file
- `create_sample.py` - Generates test files
- `test_flattener.ipynb` - Jupyter testing notebook

**`tmp/`** - All temporary files (gitignored, auto-created)
- `tmp/flats/` - Flattened workbook outputs
- `tmp/logs/` - Application logs
- `tmp/temp/` - Processing temporary files

**`dist/`** - Built executables (gitignored, created by build scripts)
- Contains standalone executables after build

### Design Principles

1. **Clean root** - Only README and .env.example at root
2. **Logical grouping** - Clear separation: production, tools, docs, dev
3. **Module names match outputs** - Easy to find code for any output file
4. **Single temp location** - Everything under `./tmp/`
5. **Dependencies with scripts** - `requirements.txt` lives with the scripts that use it

---

## How It Works

### Extraction Pipeline

```
Excel File → Load → Extract Components → Normalize → Write Files → Manifest
```

### Main Flow (flattener.py)

```python
Flattener.flatten(excel_file)
  ├─> Validate file (size, extension)
  ├─> Calculate SHA256 hash
  ├─> Load workbook (openpyxl)
  ├─> Extract metadata (author, dates, properties)
  ├─> Extract structure (sheets, visibility, order)
  ├─> Extract sheets (formulas, values, formats)
  ├─> Extract VBA (using oletools)
  ├─> Extract tables & autofilters
  ├─> Extract charts
  ├─> Extract named ranges
  └─> Generate manifest.json
```

### Output Structure

```
tmp/flats/workbook-flat-20251030T143022Z-a3f5c8d1/
├── manifest.json              File inventory + metadata
├── metadata.txt               Workbook properties
├── workbook-structure.txt     Sheet order, visibility
├── named-ranges.txt           Named ranges
├── tables.txt                 Excel tables
├── autofilters.txt            AutoFilter definitions
├── charts.txt                 Chart definitions
├── vba/                       VBA modules (if present)
│   ├── vba-summary.txt
│   ├── Module1.vba
│   └── ThisWorkbook.vba
└── sheets/
    ├── Sheet1/
    │   ├── formulas.txt       Cell formulas
    │   ├── literal-values.txt Hardcoded values
    │   ├── computed-values.txt Formula results (optional)
    │   └── formats.txt        Cell formatting
    └── Sheet2/
        └── ...
```

### Key Design Decisions

**All files always created** - Even if empty (header + "(No X found)")
- Consistency: Same files every time
- Easier scripting: No need to check if files exist
- Better diffs: Empty vs missing is clear

**Minimal normalization** - Extract as-is from Excel
- Preserve formula case and spacing
- Full numeric precision (no rounding)
- Only normalize: encoding (UTF-8), line endings (LF), cell order (row-major)

**Deterministic output** - Same input always produces same output
- Important for version control and diffs

---

## Module Reference

### Module → Output File Mapping

| Python Module | Output File(s) | Purpose |
|---------------|----------------|---------|
| `workbook_structure.py` | `workbook-structure.txt` | Sheet order, visibility, colors |
| `metadata.py` | `metadata.txt` | Workbook properties (author, dates) |
| `sheets.py` | `formulas.txt`, `literal-values.txt`, `formats.txt`, `computed-values.txt` | Cell data |
| `tables.py` | `tables.txt`, `autofilters.txt` | Excel tables & filters |
| `charts.py` | `charts.txt` | Chart definitions |
| `named_ranges.py` | `named-ranges.txt` | Named ranges |
| `vba.py` | `vba/*.vba`, `vba-summary.txt` | VBA macros |
| `manifest.py` | `manifest.json` | File inventory & metadata |

### Core Modules

**`flattener.py`** - Main orchestrator
- Coordinates all extraction modules
- Handles timeouts and error recovery
- Generates flat root directory name

**`utils.py`** - Core utilities
- Logging setup (colored console + file)
- File hashing (SHA256)
- Configuration loading (.env)
- Cell address utilities

**`normalizer.py`** - Normalization functions
- Minimal normalization (as-is philosophy)
- Line endings, text encoding
- Cell address sorting

**`manifest.py`** - Manifest generation
- Tracks all generated files with SHA256
- Records sheets, warnings, origin metadata
- JSON output

### Extraction Modules

Each extraction module follows the same pattern:

```python
def extract_X(workbook) -> List[Dict]:
    """Extract X from workbook."""
    # Extract data
    # Return structured list

def write_X_file(data: List[Dict], output_path: Path) -> None:
    """Write X data to file."""
    # Always create file (even if empty)
    # Write header
    # Write data or "(No X found)"
```

---

## Adding Features

### Add a New Extraction Type

**Example**: Extract data validation rules

1. **Create module** - `src/data_validation.py`

```python
"""Data validation extraction."""
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def extract_data_validations(wb: Workbook) -> List[Dict[str, Any]]:
    """Extract data validation rules."""
    logger.debug("Extracting data validations...")
    validations = []

    for ws in wb.worksheets:
        # Extract validation rules from worksheet
        # Add to validations list
        pass

    logger.info(f"✓ Extracted {len(validations)} validations")
    return validations

def write_validations_file(validations: List[Dict[str, Any]], output_path: Path) -> None:
    """Write validations to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# Data Validations\n')
        f.write('# ' + '=' * 50 + '\n\n')

        if not validations:
            f.write('(No data validations found)\n')
            return

        for validation in validations:
            f.write(f"Cell: {validation['cell']}\n")
            f.write(f"  Type: {validation['type']}\n")
            # ... write other properties

    logger.debug(f"Wrote validations to: {output_path}")
```

2. **Add to flattener** - Update `src/flattener.py`

```python
# Import
from .data_validation import extract_data_validations, write_validations_file

# Add method
def _extract_validations(self, wb: Workbook, flat_root: Path, manifest: Manifest) -> None:
    """Extract data validations."""
    logger.info("Extracting data validations...")
    try:
        validations = extract_data_validations(wb)
        validations_path = flat_root / 'data-validations.txt'
        write_validations_file(validations, validations_path)
        manifest.add_file(validations_path, flat_root)
    except Exception as e:
        logger.error(f"Error extracting validations: {e}", exc_info=True)
        manifest.add_warning(f"Validation extraction failed: {e}")

# Call from flatten()
def flatten(self, excel_file: Path, ...) -> Path:
    # ... existing code ...
    self._extract_validations(wb, flat_root, manifest)  # Add this line
    # ... rest of code ...
```

3. **Test** - Update `snippets/test_flattener.ipynb`

### Add a CLI Command

Update `src/__main__.py`:

```python
@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
def validate(input_file):
    """
    Validate an Excel file structure.

    Checks for issues without flattening.
    """
    # Implementation
    pass
```

### Add Configuration Option

1. Add to `.env.example`:
```bash
# Extract conditional formatting?
# Default: false
FLATTENER_INCLUDE_CONDITIONAL_FORMATTING=false
```

2. Add to `src/utils.py` in `load_config()`:
```python
config = {
    # ... existing ...
    'include_conditional_formatting': os.getenv(
        'FLATTENER_INCLUDE_CONDITIONAL_FORMATTING',
        'false'
    ).lower() == 'true',
}
```

3. Use in flattener:
```python
def __init__(self, ..., include_conditional_formatting: bool = False):
    self.include_conditional_formatting = include_conditional_formatting
```

---

## Build & Distribution

### Development Scripts

#### run_flattener.sh / run_flattener.bat

**Location**: `scripts/run_flattener.sh` (Linux/Mac) or `scripts/run_flattener.bat` (Windows)

**Purpose**: Development launcher that handles environment setup automatically

**How it works:**

1. **Navigate to component root**
   ```bash
   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   cd "$SCRIPT_DIR/.."  # Move to flattener/
   ```

2. **Check/create virtual environment**
   - Looks for `venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate.bat` (Windows)
   - If missing, creates with `python3 -m venv venv`

3. **Activate virtual environment**
   ```bash
   source "$VENV_DIR/bin/activate"  # Linux/Mac
   ```

4. **Check/install dependencies**
   - Tests if `openpyxl` is installed (proxy for all dependencies)
   - If missing, runs `pip install -r scripts/requirements.txt`

5. **Load .env file** (if exists)
   ```bash
   set -a
   source .env
   set +a
   ```

6. **Run Python module**
   ```bash
   python -m src "$@"  # Pass all arguments through
   ```

7. **Deactivate and exit**
   ```bash
   deactivate
   exit $EXIT_CODE
   ```

**Usage:**
```bash
# Must run from flattener/ directory
cd /path/to/flattener/
./scripts/run_flattener.sh flatten workbook.xlsx --log-level DEBUG
```

**Key variables:**
- `VENV_DIR="venv"` - Virtual environment directory name
- `PYTHON_CMD="python3"` - Python command to use
- Colours for output: `RED`, `GREEN`, `YELLOW`, `NC` (no colour)

#### build_package.sh / build_package.bat

**Location**: `scripts/build_package.sh` (Linux/Mac) or `scripts/build_package.bat` (Windows)

**Purpose**: Build standalone executable using PyInstaller

**How it works:**

1. **Navigate to component root**
   ```bash
   cd "$SCRIPT_DIR/.."
   ```

2. **Create/activate virtual environment** (same as run_flattener)

3. **Install dependencies**
   ```bash
   pip install -r "$SCRIPT_DIR/requirements.txt"
   ```

4. **Install PyInstaller**
   ```bash
   pip install pyinstaller
   ```

5. **Clean previous builds**
   ```bash
   rm -rf "$DIST_DIR" "$BUILD_DIR" excel-flattener.spec
   ```

6. **Run PyInstaller**
   ```bash
   pyinstaller \
       --onefile \                    # Single file output
       --name excel-flattener \       # Executable name
       --console \                    # Console app (not GUI)
       --clean \                      # Clean cache
       --noconfirm \                  # Overwrite without asking
       --hidden-import=openpyxl \     # Include modules PyInstaller might miss
       --hidden-import=openpyxl.cell \
       --hidden-import=openpyxl.styles \
       --hidden-import=openpyxl.chart \
       --hidden-import=openpyxl.worksheet \
       --hidden-import=lxml \
       --hidden-import=lxml.etree \
       --hidden-import=oletools \
       --hidden-import=oletools.olevba \
       --hidden-import=click \
       --hidden-import=dotenv \
       --collect-data openpyxl \      # Bundle openpyxl data files
       src/__main__.py                # Entry point script
   ```

7. **Report results**
   - Shows path to executable: `dist/excel-flattener` (or `.exe` on Windows)
   - Shows usage examples

**Usage:**
```bash
# Must run from flattener/ directory
cd /path/to/flattener/
./scripts/build_package.sh

# Test the built executable
./dist/excel-flattener --help
./dist/excel-flattener flatten workbook.xlsx
```

**Output structure:**
```
flattener/
├── dist/
│   └── excel-flattener          # The executable (distribute this)
├── build/                        # Build artifacts (can delete)
│   └── excel-flattener/         # Intermediate files
└── excel-flattener.spec         # PyInstaller spec file (can delete)
```

**Key variables:**
- `VENV_DIR="venv"` - Virtual environment directory
- `DIST_DIR="dist"` - Output directory for executable
- `BUILD_DIR="build"` - Build artifacts directory
- `PYTHON_CMD="python3"` - Python command

**Requirements:**
- Python must be built with shared library support (`--enable-shared`)
- Check with: `python3 -c "import sysconfig; print(sysconfig.get_config_var('Py_ENABLE_SHARED'))"`
- Should output `1` (supported) or `0` (not supported)

**Common issues:**
1. **"Python was built without a shared library"**
   - Install Python from python.org (Windows/Mac)
   - Use system package manager (Linux): `apt-get install python3-dev`
   - Use Docker image: `FROM python:3.12-slim`

2. **Build succeeds but executable fails**
   - Add missing modules as `--hidden-import=module.name` in build script
   - Check build log for import errors

3. **Executable is very large (>100MB)**
   - Normal! PyInstaller bundles Python + all dependencies
   - Typical size: 50-150MB depending on dependencies

### Development Workflow

**Daily development:**
```bash
# Run tests/experiments
./scripts/run_flattener.sh flatten test-file.xlsx

# Or activate venv once and work directly
source venv/bin/activate
python -m src flatten workbook.xlsx
python -m src config
python -m src info workbook.xlsx
deactivate
```

**Before committing:**
```bash
# Test clean build
rm -rf venv build dist *.spec
./scripts/run_flattener.sh flatten sample.xlsx

# Verify output structure
tree tmp/flats/ -L 3
```

**Before releasing:**
```bash
# Build executable
./scripts/build_package.sh

# Test executable
./dist/excel-flattener --help
./dist/excel-flattener flatten snippets/sample.xlsx

# Verify it works without Python environment
deactivate
unset PYTHONPATH
./dist/excel-flattener flatten snippets/sample.xlsx
```

### Distribution Options

**Option 1: Source Distribution**
- Share entire `flattener/` folder (or zip/tar.gz)
- Users run `./scripts/run_flattener.sh` (auto-setup)
- **Requirements**: Python 3.9+
- **Pros**: Easy to modify, cross-platform
- **Cons**: Requires Python installation

**Option 2: Binary Distribution (Recommended)**
- Share just `dist/excel-flattener` (or `.exe`)
- **Requirements**: None (standalone)
- **Pros**: No Python needed, single file
- **Cons**: Platform-specific, large file size

Create a simple README for users:
```bash
cat > dist/README.txt << EOF
Excel Flattener - Standalone Executable

Usage:
  ./excel-flattener flatten workbook.xlsx
  ./excel-flattener --help

Configuration:
  Create a .env file in the same directory:
    FLATTENER_OUTPUT_DIR=./output
    FLATTENER_LOG_LEVEL=DEBUG

  Or use environment variables:
    export FLATTENER_OUTPUT_DIR=./output
    ./excel-flattener flatten workbook.xlsx
EOF
```

**Option 3: PyPI Package (Future)**
```bash
pip install excel-flattener
excel-flattener flatten workbook.xlsx
```

### PyInstaller Configuration Details

**Why `--onefile`?**
- Creates single executable (easier distribution)
- Extracts to temp on first run (~2-3 second startup delay)
- Alternative: `--onedir` (faster startup, but many files)

**Why all the `--hidden-import`?**
- PyInstaller analyses imports statically
- Dynamic imports (e.g., `importlib.import_module()`) are missed
- openpyxl uses dynamic imports internally
- Better to over-specify than have runtime errors

**Why `--collect-data openpyxl`?**
- openpyxl includes data files (XML schemas, etc.)
- These aren't Python code, so must be explicitly bundled

**Spec file:**
After first build, PyInstaller creates `excel-flattener.spec`. You can:
1. Edit this file for advanced customization
2. Rebuild with: `pyinstaller excel-flattener.spec`
3. Version control it for reproducible builds

---

## Configuration

### Environment Variables

All prefixed with `FLATTENER_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLATTENER_OUTPUT_DIR` | `./tmp/flats` | Flat output directory |
| `FLATTENER_LOG_DIR` | `./tmp/logs` | Log file directory |
| `FLATTENER_LOG_LEVEL` | `INFO` | Logging level |
| `FLATTENER_INCLUDE_COMPUTED` | `false` | Extract computed values? |
| `FLATTENER_EXTRACTION_TIMEOUT` | `900` | Max extraction time (seconds) |
| `FLATTENER_MAX_FILE_SIZE_MB` | `200` | Max input file size (MB) |
| `FLATTENER_TEMP_DIR` | `./tmp/temp` | Temporary processing directory |

### Configuration Files

**Development**: `.env` in component root
**Production**: `.env` next to executable

Copy `.env.example` to `.env` and customize.

### Logging

**Console**: Colored output, respects `LOG_LEVEL`
**File**: Plain text, always DEBUG level, written to `LOG_DIR`

Format: `[YYYY-MM-DD HH:MM:SS] LEVEL | module | message`

---

## Testing

### Manual Testing

```bash
# Using Jupyter notebook
cd snippets/
jupyter notebook test_flattener.ipynb

# Using CLI
./scripts/run_flattener.sh flatten snippets/sample.xlsx
```

### Creating Test Files

```bash
# Generate sample workbook
cd snippets/
python create_sample.py
```

Modify `create_sample.py` to add specific features for testing.

### Test Scenarios

1. **Empty workbook** - All files should be created with "(No X found)"
2. **Large workbook** - Test timeout handling
3. **Password-protected VBA** - Should extract successfully (oletools)
4. **Hidden sheets** - Should mark as visible=false
5. **Dynamic arrays** - Should extract spill formulas
6. **All formats** - .xlsx, .xlsm, .xlsb, .xls

### Verifying Output

```bash
# Check all files created
find tmp/flats/workbook-flat-*/ -type f

# Check for empty files (should have headers)
cat tmp/flats/workbook-flat-*/tables.txt

# Verify determinism (same hash each time)
python -m src flatten test.xlsx
python -m src flatten test.xlsx
diff -r tmp/flats/test-flat-*1/ tmp/flats/test-flat-*2/
```

---

## Troubleshooting

### Common Issues

**Import errors after renaming module**
- Update imports in `flattener.py`
- Update imports in any tests

**PyInstaller missing modules**
- Add `--hidden-import=module_name` to build scripts

**Files not created**
- Check that extraction module calls `write_X_file()` always
- Verify file isn't failing silently (check logs)

**Wrong file path in output**
- Module name should match output file name
- Check `flat_root / 'filename.txt'` in flattener.py

### Debug Mode

```bash
# Enable debug logging
export FLATTENER_LOG_LEVEL=DEBUG
./scripts/run_flattener.sh flatten workbook.xlsx

# Check detailed logs
tail -f tmp/logs/flattener_*.log
```

---

## Code Style

### Conventions

- **Language**: British English in all user-facing text
  - "colour" not "color"
  - "normalisation" not "normalization"
- **Docstrings**: Google-style
- **Type hints**: Use where beneficial
- **Line length**: 100 characters recommended
- **Imports**: Standard library, third-party, local (grouped)

### Naming

- **Modules**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions**: `lowercase_with_underscores()`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Private**: `_leading_underscore`

### Example

```python
"""
Module docstring.

Brief description of what this module does.
"""
import logging
from pathlib import Path
from typing import Dict, List, Any

from openpyxl import Workbook

from .utils import get_file_hash

logger = logging.getLogger(__name__)


def extract_something(wb: Workbook) -> List[Dict[str, Any]]:
    """
    Extract something from workbook.

    Args:
        wb: Openpyxl workbook object

    Returns:
        List of something dictionaries

    Raises:
        ValueError: If workbook is invalid
    """
    logger.debug("Extracting something...")
    # Implementation
    return []
```

---

## Version History

**v2.1.0** - Current
- Initial clean implementation
- Minimal normalization philosophy
- All features always enabled
- Clean folder structure

---

## Quick Reference

### Adding Features Checklist

- [ ] Create new module in `src/`
- [ ] Import in `flattener.py`
- [ ] Add extraction method `_extract_X()`
- [ ] Call from `flatten()` method
- [ ] Update tests in `snippets/test_flattener.ipynb`
- [ ] Add to this documentation

### File Locations

| Purpose | Location |
|---------|----------|
| Add production code | `src/` |
| Add build script | `scripts/` |
| Add documentation | `docs/` (this file) |
| Add test/example | `snippets/` |
| Add dependency | `scripts/requirements.txt` |

### Useful Commands

```bash
# Clean everything
rm -rf tmp/ dist/ venv/

# Run from source
python -m src flatten workbook.xlsx

# Build executable
./scripts/build_package.sh

# View logs
tail -f tmp/logs/flattener_*.log

# Test with sample
./scripts/run_flattener.sh flatten snippets/sample.xlsx
```

---

**Last Updated**: 2025-10-30
**Version**: 2.1.0
