@echo off
REM Build script for Excel Flattener (Windows)
REM Creates a single-file executable using PyInstaller

setlocal enabledelayedexpansion

REM Get script directory and move to component root
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\.."

echo ====================================
echo Excel Flattener - Build Script
echo ====================================
echo.

REM Configuration
set "VENV_DIR=venv"
set "DIST_DIR=dist"
set "BUILD_DIR=build"
set "PYTHON_CMD=python"

REM Check if virtual environment exists
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
echo [*] Installing dependencies...
pip install -r "%SCRIPT_DIR%\requirements.txt"
if errorlevel 1 (
    echo [X] Failed to install dependencies
    exit /b 1
)

REM Install PyInstaller
echo [*] Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [X] Failed to install PyInstaller
    exit /b 1
)

REM Clean previous builds
if exist "%DIST_DIR%" (
    echo [*] Cleaning previous build...
    rmdir /s /q "%DIST_DIR%"
)
if exist "%BUILD_DIR%" (
    rmdir /s /q "%BUILD_DIR%"
)

REM Build executable
echo [*] Building executable with PyInstaller...
echo.

pyinstaller ^
    --onefile ^
    --name excel-flattener ^
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
    --add-data "src;src" ^
    -m src

if errorlevel 1 (
    echo.
    echo [X] Build failed
    deactivate
    exit /b 1
)

echo.
echo ====================================
echo [+] Build successful!
echo ====================================
echo.
echo Executable: %CD%\%DIST_DIR%\excel-flattener.exe
echo.
echo Usage:
echo   excel-flattener.exe flatten workbook.xlsx
echo   excel-flattener.exe --help
echo.

REM Deactivate virtual environment
deactivate

exit /b 0
