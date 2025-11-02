@echo off
setlocal

REM ============================================================================
REM SECTION 1: VARIABLE DEFINITIONS
REM ============================================================================

set "VENV_DIR=.venv"
set "WORKFLOW_CONFIG=workflow_definitions\default.yaml"
set "PYTHON_CMD=python"
set "REQUIREMENTS_FILE=requirements.txt"

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
REM SECTION 4: RUN WORKFLOW
REM ============================================================================

echo Running workflow with config: %WORKFLOW_CONFIG%
python main.py workflow "%WORKFLOW_CONFIG%"
