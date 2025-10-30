#!/usr/bin/env bash
# =============================================================================
# Excel Flattener - Development Launcher (Linux/Mac)
# =============================================================================
# Automatically sets up virtual environment and runs the flattener
#
# Usage: ./scripts/run_flattener.sh flatten workbook.xlsx [OPTIONS]
#
# IMPORTANT: Must run from flattener/ directory (not from scripts/)
#   cd /path/to/flattener/
#   ./scripts/run_flattener.sh flatten workbook.xlsx
# =============================================================================

set -e  # Exit on error

# =============================================================================
# SECTION 1: CONFIGURATION
# =============================================================================

# Directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPONENT_ROOT="$SCRIPT_DIR/.."
VENV_DIR="venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

# Python command (change if needed)
PYTHON_CMD="python3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

# =============================================================================
# SECTION 2: VIRTUAL ENVIRONMENT MANAGEMENT
# =============================================================================

# Navigate to component root
cd "$COMPONENT_ROOT"

# Check if virtual environment exists, create if needed
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${YELLOW}[!] Virtual environment not found${NC}"
    echo -e "${YELLOW}[*] Creating virtual environment...${NC}"

    if ! $PYTHON_CMD -m venv "$VENV_DIR"; then
        echo -e "${RED}[X] Failed to create virtual environment${NC}"
        echo -e "${RED}    Make sure Python 3.9+ is installed${NC}"
        exit 1
    fi

    echo -e "${GREEN}[+] Virtual environment created${NC}"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Load .env file if it exists (optional configuration)
if [ -f ".env" ]; then
    echo -e "${GREEN}[+] Loading environment from .env${NC}"
    set -a  # Auto-export variables
    source .env
    set +a
fi

# =============================================================================
# SECTION 3: RUN FLATTENER
# =============================================================================

# Run the flattener CLI with all arguments passed through
# Example calls:
#   ./scripts/run_flattener.sh flatten workbook.xlsx
#   ./scripts/run_flattener.sh flatten workbook.xlsx --include-computed
#   ./scripts/run_flattener.sh flatten workbook.xlsx -o ./output --log-level DEBUG
#   ./scripts/run_flattener.sh config
#   ./scripts/run_flattener.sh info workbook.xlsx
#   ./scripts/run_flattener.sh --help

python -m src "$@"
EXIT_CODE=$?

# Deactivate virtual environment and exit
deactivate
exit $EXIT_CODE
