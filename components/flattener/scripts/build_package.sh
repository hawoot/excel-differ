#!/usr/bin/env bash
# =============================================================================
# Excel Flattener - Build Script (Linux/Mac)
# =============================================================================
# Creates a single-file executable using PyInstaller
#
# Usage: ./scripts/build_package.sh
#
# IMPORTANT: Must run from flattener/ directory (not from scripts/)
#   cd /path/to/flattener/
#   ./scripts/build_package.sh
#
# Output: dist/excel-flattener (standalone executable)
# =============================================================================

set -e  # Exit on error

# =============================================================================
# SECTION 1: CONFIGURATION
# =============================================================================

# Directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPONENT_ROOT="$SCRIPT_DIR/.."
VENV_DIR="$COMPONENT_ROOT/openpyxl_impl/venv"
DIST_DIR="dist"
BUILD_DIR="build"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

# Python command (change if needed)
PYTHON_CMD="python3"

# Entry point for PyInstaller
ENTRY_POINT="openpyxl_impl/src/__main__.py"

# Executable name
EXECUTABLE_NAME="excel-flattener"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# =============================================================================
# SECTION 2: VIRTUAL ENVIRONMENT & DEPENDENCIES
# =============================================================================

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}Excel Flattener - Build Script${NC}"
echo -e "${BLUE}====================================${NC}"
echo

# Navigate to component root
cd "$COMPONENT_ROOT"

# Check if virtual environment exists, create if needed
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${YELLOW}[*] Creating virtual environment...${NC}"

    if ! $PYTHON_CMD -m venv "$VENV_DIR"; then
        echo -e "${RED}[X] Failed to create virtual environment${NC}"
        exit 1
    fi

    echo -e "${GREEN}[+] Virtual environment created${NC}"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install dependencies
echo -e "${YELLOW}[*] Installing dependencies from $REQUIREMENTS_FILE...${NC}"
if ! pip install -r "$REQUIREMENTS_FILE"; then
    echo -e "${RED}[X] Failed to install dependencies${NC}"
    deactivate
    exit 1
fi

# Install PyInstaller
echo -e "${YELLOW}[*] Installing PyInstaller...${NC}"
if ! pip install pyinstaller; then
    echo -e "${RED}[X] Failed to install PyInstaller${NC}"
    deactivate
    exit 1
fi

# Clean previous builds
if [ -d "$DIST_DIR" ] || [ -d "$BUILD_DIR" ]; then
    echo -e "${YELLOW}[*] Cleaning previous build artifacts...${NC}"
    rm -rf "$DIST_DIR" "$BUILD_DIR" "$EXECUTABLE_NAME.spec"
fi

# =============================================================================
# SECTION 3: BUILD EXECUTABLE
# =============================================================================

echo -e "${YELLOW}[*] Building executable with PyInstaller...${NC}"
echo

# Build with PyInstaller
# --onefile             Single executable file
# --name                Output executable name
# --console             Console application (not GUI)
# --clean               Clean PyInstaller cache
# --noconfirm           Overwrite output without confirmation
# --hidden-import       Explicitly include modules PyInstaller might miss
# --collect-data        Bundle data files from package
# Entry point: src/__main__.py

pyinstaller \
    --onefile \
    --name "$EXECUTABLE_NAME" \
    --console \
    --clean \
    --noconfirm \
    --hidden-import=openpyxl \
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
    --collect-data openpyxl \
    "$ENTRY_POINT"

# Check if build succeeded
if [ $? -ne 0 ]; then
    echo
    echo -e "${RED}[X] Build failed${NC}"
    deactivate
    exit 1
fi

# Deactivate virtual environment
deactivate

# Show success message
echo
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}[+] Build successful!${NC}"
echo -e "${GREEN}====================================${NC}"
echo
echo -e "Executable: ${YELLOW}$(pwd)/$DIST_DIR/$EXECUTABLE_NAME${NC}"
echo
echo "Usage:"
echo "  ./dist/$EXECUTABLE_NAME flatten workbook.xlsx"
echo "  ./dist/$EXECUTABLE_NAME flatten workbook.xlsx --include-computed -o ./output"
echo "  ./dist/$EXECUTABLE_NAME config"
echo "  ./dist/$EXECUTABLE_NAME --help"
echo

exit 0
