#!/bin/bash
set -e

# ============================================================================
# SECTION 1: VARIABLE DEFINITIONS
# ============================================================================

VENV_DIR=".venv"
OUTPUT_DIR="dist"
EXE_NAME="excel-differ"
BUILD_DIR="build"
SPEC_DIR="build"
PYTHON_CMD="python3"
REQUIREMENTS_FILE="requirements.txt"
ENTRY_POINT="main.py"

# ============================================================================
# SECTION 2: VIRTUAL ENVIRONMENT SETUP
# ============================================================================

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    $PYTHON_CMD -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# ============================================================================
# SECTION 3: INSTALL DEPENDENCIES
# ============================================================================

echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo "Installing dependencies from $REQUIREMENTS_FILE..."
pip install -r "$REQUIREMENTS_FILE" --quiet

# ============================================================================
# SECTION 4: BUILD EXECUTABLE
# ============================================================================

echo "Cleaning previous build artifacts..."
rm -rf "$BUILD_DIR" "$OUTPUT_DIR"

echo "Building executable with PyInstaller..."
pyinstaller \
    --onefile \
    --name "$EXE_NAME" \
    --distpath "$OUTPUT_DIR" \
    --workpath "$BUILD_DIR" \
    --specpath "$SPEC_DIR" \
    --clean \
    "$ENTRY_POINT"

echo ""
echo "Build complete! Executable location: $OUTPUT_DIR/$EXE_NAME"
