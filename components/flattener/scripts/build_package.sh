#!/usr/bin/env bash
# Build script for Excel Flattener (Linux/Mac)
# Creates a single-file executable using PyInstaller

set -e

# Get script directory and move to component root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Colour

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}Excel Flattener - Build Script${NC}"
echo -e "${BLUE}====================================${NC}"
echo

# Configuration
VENV_DIR="venv"
DIST_DIR="dist"
BUILD_DIR="build"
PYTHON_CMD="python3"

# Check if virtual environment exists
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
echo -e "${YELLOW}[*] Installing dependencies...${NC}"
if ! pip install -r "$SCRIPT_DIR/requirements.txt"; then
    echo -e "${RED}[X] Failed to install dependencies${NC}"
    exit 1
fi

# Install PyInstaller
echo -e "${YELLOW}[*] Installing PyInstaller...${NC}"
if ! pip install pyinstaller; then
    echo -e "${RED}[X] Failed to install PyInstaller${NC}"
    exit 1
fi

# Clean previous builds
if [ -d "$DIST_DIR" ] || [ -d "$BUILD_DIR" ]; then
    echo -e "${YELLOW}[*] Cleaning previous build...${NC}"
    rm -rf "$DIST_DIR" "$BUILD_DIR" excel-flattener.spec
fi

# Build executable
echo -e "${YELLOW}[*] Building executable with PyInstaller...${NC}"
echo

pyinstaller \
    --onefile \
    --name excel-flattener \
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
    --add-data "src:src" \
    -m src

if [ $? -ne 0 ]; then
    echo
    echo -e "${RED}[X] Build failed${NC}"
    deactivate
    exit 1
fi

echo
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}[+] Build successful!${NC}"
echo -e "${GREEN}====================================${NC}"
echo
echo -e "Executable: ${YELLOW}$(pwd)/$DIST_DIR/excel-flattener${NC}"
echo
echo "Usage:"
echo "  ./dist/excel-flattener flatten workbook.xlsx"
echo "  ./dist/excel-flattener --help"
echo

# Deactivate virtual environment
deactivate

exit 0
