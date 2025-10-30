@echo off
REM =============================================================================
REM Excel Flattener - Build Script (Windows)
REM =============================================================================
REM Creates a single-file executable using PyInstaller
REM
REM Usage: scripts\build_package.bat
REM
REM IMPORTANT: Must run from flattener\ directory (not from scripts\)
REM   cd C:\path\to\flattener
REM   scripts\build_package.bat
REM
REM Output: dist\excel-flattener.exe (standalone executable)
REM =============================================================================

setlocal enabledelayedexpansion

REM =============================================================================
REM SECTION 1: CONFIGURATION
REM =============================================================================

REM Directory paths
set "SCRIPT_DIR=%~dp0"
set "COMPONENT_ROOT=%SCRIPT_DIR%.."
set "VENV_DIR=venv"
set "DIST_DIR=dist"
set "BUILD_DIR=build"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%requirements.txt"

REM Python command (change if needed)
set "PYTHON_CMD=python"

REM Entry point for PyInstaller
set "ENTRY_POINT=src\__main__.py"

REM Executable name
set "EXECUTABLE_NAME=excel-flattener"

REM =============================================================================
REM SECTION 2: VIRTUAL ENVIRONMENT & DEPENDENCIES
REM =============================================================================

echo ====================================
echo Excel Flattener - Build Script
echo ====================================
echo.

REM Navigate to component root
cd /d "%COMPONENT_ROOT%"

REM Check if virtual environment exists, create if needed
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [*] Creating virtual environment...
    %PYTHON_CMD% -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [X] Failed to create virtual environment
        exit /b 1
    )
    echo [+] Virtual environment created
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Install dependencies
echo [*] Installing dependencies from %REQUIREMENTS_FILE%...
pip install -r "%REQUIREMENTS_FILE%"
if errorlevel 1 (
    echo [X] Failed to install dependencies
    deactivate
    exit /b 1
)

REM Install PyInstaller
echo [*] Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [X] Failed to install PyInstaller
    deactivate
    exit /b 1
)

REM Clean previous builds
if exist "%DIST_DIR%" (
    echo [*] Cleaning previous build artifacts...
    rmdir /s /q "%DIST_DIR%"
)
if exist "%BUILD_DIR%" (
    rmdir /s /q "%BUILD_DIR%"
)
if exist "%EXECUTABLE_NAME%.spec" (
    del "%EXECUTABLE_NAME%.spec"
)

REM =============================================================================
REM SECTION 3: BUILD EXECUTABLE
REM =============================================================================

echo [*] Building executable with PyInstaller...
echo.

REM Build with PyInstaller
REM --onefile             Single executable file
REM --name                Output executable name
REM --console             Console application (not GUI)
REM --clean               Clean PyInstaller cache
REM --noconfirm           Overwrite output without confirmation
REM --hidden-import       Explicitly include modules PyInstaller might miss
REM --collect-data        Bundle data files from package
REM Entry point: src\__main__.py

pyinstaller ^
    --onefile ^
    --name %EXECUTABLE_NAME% ^
    --console ^
    --clean ^
    --noconfirm ^
    --hidden-import=openpyxl ^
    --hidden-import=openpyxl.cell ^
    --hidden-import=openpyxl.styles ^
    --hidden-import=openpyxl.chart ^
    --hidden-import=openpyxl.worksheet ^
    --hidden-import=lxml ^
    --hidden-import=lxml.etree ^
    --hidden-import=oletools ^
    --hidden-import=oletools.olevba ^
    --hidden-import=click ^
    --hidden-import=dotenv ^
    --collect-data openpyxl ^
    %ENTRY_POINT%

REM Check if build succeeded
if errorlevel 1 (
    echo.
    echo [X] Build failed
    deactivate
    exit /b 1
)

REM Deactivate virtual environment
deactivate

REM Show success message
echo.
echo ====================================
echo [+] Build successful!
echo ====================================
echo.
echo Executable: %CD%\%DIST_DIR%\%EXECUTABLE_NAME%.exe
echo.
echo Usage:
echo   excel-flattener.exe flatten workbook.xlsx
echo   excel-flattener.exe flatten workbook.xlsx --include-computed -o .\output
echo   excel-flattener.exe config
echo   excel-flattener.exe --help
echo.

exit /b 0
