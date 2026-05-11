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

TITLE ResKiosk - Build Hub Executable
CLS

ECHO ========================================================
ECHO   ResKiosk - Build Hub Executable (PyInstaller)
ECHO ========================================================
ECHO.

REM Navigate to project root (one level up from TO RUN\)
cd /d "%~dp0\.."
ECHO Working directory: %CD%
ECHO.

REM 1. Ensure virtual environment exists
IF NOT EXIST "venv\Scripts\python.exe" (
    ECHO ERROR: Python virtual environment not found.
    ECHO Please run "01_install_deps.bat" first.
    ECHO.
    PAUSE
    EXIT /B 1
)

REM 2. Check PyInstaller is installed
ECHO [1/4] Checking PyInstaller...
"venv\Scripts\python.exe" -c "import PyInstaller; print(f'  PyInstaller {PyInstaller.__version__} found.')" 2>nul
IF %ERRORLEVEL% NEQ 0 (
    ECHO   PyInstaller not found. Installing...
    "venv\Scripts\pip.exe" install pyinstaller==6.3.0
    IF %ERRORLEVEL% NEQ 0 (
        ECHO ERROR: Failed to install PyInstaller.
        PAUSE
        EXIT /B 1
    )
)

REM 3. Build console frontend (if not already built)
ECHO.
ECHO [2/4] Checking console frontend build...
IF NOT EXIST "console\dist\index.html" (
    ECHO   Console not built. Building now...
    cd console
    call npm install
    call npm run build
    cd ..
    IF NOT EXIST "console\dist\index.html" (
        ECHO WARNING: Console build failed. The exe will work but won't have the web UI.
    )
) ELSE (
    ECHO   Console frontend already built.
)

REM 4. Check models
ECHO.
ECHO [3/4] Checking models...
IF EXIST "packaging\hub_models\model.safetensors" (
    ECHO   MiniLM embedding model found.
) ELSE (
    ECHO   WARNING: MiniLM model not found in packaging\hub_models\.
    ECHO   Run "02_download_models.bat" first, or the exe will lack embedding support.
)

REM 5. Run PyInstaller
ECHO.
ECHO [4/4] Building executable with PyInstaller...
ECHO   This may take several minutes...
ECHO.

"venv\Scripts\pyinstaller.exe" "packaging\reskiosk-hub.spec" --noconfirm
IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    ECHO ========================================================
    ECHO   BUILD FAILED
    ECHO ========================================================
    ECHO   Check the error messages above for details.
    ECHO.
    PAUSE
    EXIT /B 1
)

ECHO.
ECHO ========================================================
ECHO   BUILD SUCCESSFUL!
ECHO ========================================================
ECHO.
ECHO   Output: dist\ResKiosk-Hub\ResKiosk-Hub.exe
ECHO.
ECHO   To run: double-click dist\ResKiosk-Hub\ResKiosk-Hub.exe
ECHO   The hub will start on http://localhost:8000
ECHO.
ECHO ========================================================
ENDLOCAL
PAUSE
