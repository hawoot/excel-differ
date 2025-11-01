@echo off
REM =============================================================================
REM Excel Flattener - Development Launcher (Windows)
REM =============================================================================
REM Automatically sets up virtual environment and runs the flattener
REM
REM Usage: scripts\run_flattener.bat flatten .\snippets\sample.xlsx [OPTIONS]
REM
REM IMPORTANT: Must run from flattener\ directory (not from scripts\)
REM   cd C:\path\to\flattener
REM   scripts\run_flattener.bat flatten .\snippets\sample.xlsx
REM =============================================================================

setlocal enabledelayedexpansion

REM =============================================================================
REM SECTION 1: CONFIGURATION
REM =============================================================================

REM Directory paths
set "SCRIPT_DIR=%~dp0"
set "COMPONENT_ROOT=%SCRIPT_DIR%.."
set "VENV_DIR=openpyxl_impl\venv"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%requirements.txt"

REM Python command (change if needed)
set "PYTHON_CMD=python"

REM =============================================================================
REM SECTION 2: VIRTUAL ENVIRONMENT MANAGEMENT
REM =============================================================================

REM Navigate to component root
cd /d "%COMPONENT_ROOT%"

REM Check if virtual environment exists, create if needed
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [!] Virtual environment not found
    echo [*] Creating virtual environment...

    %PYTHON_CMD% -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [X] Failed to create virtual environment
        echo     Make sure Python 3.9+ is installed
        exit /b 1
    )

    echo [+] Virtual environment created
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"
REM Install dependencies
echo [*] Installing dependencies from %REQUIREMENTS_FILE%...
pip install -r "%REQUIREMENTS_FILE%"

REM Load .env file if it exists (optional configuration)
if exist ".env" (
    echo [+] Loading environment from .env
    for /f "usebackq tokens=*" %%a in (".env") do (
        set "line=%%a"
        REM Skip comments and empty lines
        if not "!line:~0,1!"=="#" if not "!line!"=="" (
            set "%%a"
        )
    )
)

REM =============================================================================
REM SECTION 3: RUN FLATTENER
REM =============================================================================

REM Run the flattener CLI with all arguments passed through
REM Example calls:
REM   cd components\flattener
REM   scripts\run_flattener.bat flatten .\snippets\sample.xlsx
REM Minimal options:
REM   scripts\run_flattener.bat flatten .\snippets\sample.xlsx --no-computed --no-formats --no-literal
REM Default options:
REM   scripts\run_flattener.bat flatten .\snippets\sample.xlsx --no-computed --include-literal --include-formats
REM Maximum options:
REM   scripts\run_flattener.bat flatten .\snippets\sample.xlsx --no-computed --include-literal --include-formats

REM Debugging options:
REM   scripts\run_flattener.bat flatten .\snippets\sample.xlsx -o ./output --log-level DEBUG

REM With commit options:
REM   scripts\run_flattener.bat flatten .\snippets\sample.xlsx --origin-repo repo_name --origin-path /dir1/file1 --origin-commit commitId --origin-commit-message "Update flattened data"

REM   scripts\run_flattener.bat config
REM   scripts\run_flattener.bat info .\snippets\sample.xlsx
REM   scripts\run_flattener.bat --help

python -m openpyxl_impl.src %*
set EXIT_CODE=%ERRORLEVEL%

REM Deactivate virtual environment and exit
deactivate
exit /b %EXIT_CODE%
