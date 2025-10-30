@echo off
REM Launcher script for Excel Flattener (Windows)
REM Automatically sets up virtual environment if needed

setlocal enabledelayedexpansion

REM Get script directory and move to component root
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\.."

REM Configuration
set "VENV_DIR=venv"
set "PYTHON_CMD=python"

REM Check if virtual environment exists
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [!] Virtual environment not found
    echo [*] Creating virtual environment...
    %PYTHON_CMD% -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [X] Failed to create virtual environment
        echo [*] Make sure Python 3.9+ is installed
        exit /b 1
    )
    echo [+] Virtual environment created
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Check if dependencies are installed
pip show openpyxl >nul 2>&1
if errorlevel 1 (
    echo [*] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [X] Failed to install dependencies
        exit /b 1
    )
    echo [+] Dependencies installed
)

REM Load .env file if it exists
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

REM Run CLI with all arguments passed through
python -m src %*
set "EXIT_CODE=%errorlevel%"

REM Deactivate virtual environment
deactivate

exit /b %EXIT_CODE%
