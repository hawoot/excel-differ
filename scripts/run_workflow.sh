#!/bin/bash
set -e

# ============================================================================
# SECTION 1: VARIABLE DEFINITIONS
# ============================================================================

VENV_DIR=".venv"
WORKFLOW_CONFIG="workflow_definitions/default.yaml"
PYTHON_CMD="python3"
REQUIREMENTS_FILE="requirements.txt"

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
# SECTION 4: RUN WORKFLOW
# ============================================================================

echo "Running workflow with config: $WORKFLOW_CONFIG"
python main.py workflow "$WORKFLOW_CONFIG"
