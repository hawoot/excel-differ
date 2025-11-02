@echo off
setlocal

REM ============================================================================
REM SECTION 1: VARIABLE DEFINITIONS
REM ============================================================================

set "VENV_DIR=.venv"
set "OUTPUT_DIR=dist"
set "EXE_NAME=excel-differ.exe"
set "BUILD_DIR=build"
set "SPEC_DIR=build"
set "PYTHON_CMD=python"
set "REQUIREMENTS_FILE=requirements.txt"
set "ENTRY_POINT=main.py"

REM ============================================================================
REM SECTION 2: VIRTUAL ENVIRONMENT SETUP
REM ============================================================================

if not exist "%VENV_DIR%" (
    echo Creating virtual environment in %VENV_DIR%...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 exit /b 1
)

echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 exit /b 1

REM ============================================================================
REM SECTION 3: INSTALL DEPENDENCIES
REM ============================================================================

echo Upgrading pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 exit /b 1

echo Installing dependencies from %REQUIREMENTS_FILE%...
pip install -r "%REQUIREMENTS_FILE%" --quiet
if errorlevel 1 exit /b 1

REM ============================================================================
REM SECTION 4: BUILD EXECUTABLE
REM ============================================================================

echo Cleaning previous build artifacts...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"

echo Building executable with PyInstaller...
pyinstaller ^
    --onefile ^
    --name excel-differ ^
    --distpath "%OUTPUT_DIR%" ^
    --workpath "%BUILD_DIR%" ^
    --specpath "%SPEC_DIR%" ^
    --clean ^
    "%ENTRY_POINT%"

if errorlevel 1 exit /b 1

echo.
echo Build complete! Executable location: %OUTPUT_DIR%\%EXE_NAME%
