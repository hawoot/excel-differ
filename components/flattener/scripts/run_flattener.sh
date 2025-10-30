#!/usr/bin/env bash
# Launcher script for Excel Flattener (Linux/Mac)
# Automatically sets up virtual environment if needed

set -e

# Get script directory and move to component root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Configuration
VENV_DIR="venv"
PYTHON_CMD="python3"

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Colour

# Check if virtual environment exists
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${YELLOW}[!] Virtual environment not found${NC}"
    echo -e "${YELLOW}[*] Creating virtual environment...${NC}"

    if ! $PYTHON_CMD -m venv "$VENV_DIR"; then
        echo -e "${RED}[X] Failed to create virtual environment${NC}"
        echo -e "${RED}[*] Make sure Python 3.9+ is installed${NC}"
        exit 1
    fi

    echo -e "${GREEN}[+] Virtual environment created${NC}"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Check if dependencies are installed
if ! pip show openpyxl &>/dev/null; then
    echo -e "${YELLOW}[*] Installing dependencies...${NC}"

    if ! pip install -r "$SCRIPT_DIR/requirements.txt"; then
        echo -e "${RED}[X] Failed to install dependencies${NC}"
        exit 1
    fi

    echo -e "${GREEN}[+] Dependencies installed${NC}"
fi

# Load .env file if it exists
if [ -f ".env" ]; then
    echo -e "${GREEN}[+] Loading environment from .env${NC}"
    set -a
    source .env
    set +a
fi

# Run CLI with all arguments passed through
python -m src "$@"
EXIT_CODE=$?

# Deactivate virtual environment
deactivate

exit $EXIT_CODE
