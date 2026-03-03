@echo off
SETLOCAL EnableDelayedExpansion

REM Keep window open when launched via Explorer (cmd /c ...)
REM Detect /c in the original cmd line; if present and not already wrapped, relaunch under cmd /k.
echo %cmdcmdline% | find /i "/c" >nul
IF NOT ERRORLEVEL 1 (
    IF /I "%~1" NEQ "inner" (
        start "" cmd /k call "%~f0" inner
        GOTO :EOF
    )
    SHIFT
)

TITLE ResKiosk - Install Dependencies
CLS

ECHO ========================================================
ECHO   ResKiosk - Dependency Installer
ECHO ========================================================
ECHO.

REM Navigate to project root (one level up from TO RUN\)
cd /d "%~dp0\.."
ECHO Working directory: %CD%

REM 1. Check Python
ECHO [1/5] Checking Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: Python is not installed or not in PATH.
    ECHO Please install Python 3.10+ from https://www.python.org/downloads/
    ECHO Make sure to check "Add Python to PATH" during installation.
    EXIT /B 1
)
ECHO Python found.

REM 2. Create / reuse virtual environment
ECHO.
ECHO [2/5] Setting up Python virtual environment...
IF NOT EXIST "venv" (
    python -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        ECHO ERROR: Failed to create virtual environment.
        EXIT /B 1
    )
    ECHO venv created.
) ELSE (
    ECHO venv already exists.
)

REM 3. Install Python dependencies
ECHO.
ECHO [3/5] Installing Python dependencies from requirements.txt...
call "venv\Scripts\activate.bat"
pip install --no-input -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: Failed to install Python dependencies.
    EXIT /B 1
)

REM 4. Install Node.js dependencies and build admin console
ECHO.
ECHO [4/5] Installing Node.js dependencies for admin console...
node --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO WARNING: Node.js is not installed or not in PATH.
    ECHO The admin console will not be built until Node.js is installed.
) ELSE (
    ECHO Node.js found.
    cd console
    call npm install --yes
    IF %ERRORLEVEL% NEQ 0 (
        ECHO WARNING: npm install failed. Check Node.js/npm installation.
        ECHO You can rerun this script after fixing Node.js.
    ) ELSE (
        ECHO npm dependencies installed successfully.
        ECHO [5/5] Building admin console ^(Emergency Calls, Shelter Config inventory, etc.^)...
        call npm run build
        IF %ERRORLEVEL% NEQ 0 (
            ECHO WARNING: npm run build failed. Hub will still run but console may be outdated.
        ) ELSE (
            ECHO Console built. Hub will serve it from console\dist
        )
    )
    cd ..
)

ECHO.
ECHO ========================================================
ECHO   Dependency installation complete.
ECHO   Next: Run "02_download_models.bat"
ECHO ========================================================
ECHO.


