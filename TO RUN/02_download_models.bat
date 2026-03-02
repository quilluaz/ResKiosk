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

TITLE ResKiosk - Download Models
CLS

ECHO ========================================================
ECHO   ResKiosk - Offline Model Downloader
ECHO ========================================================
ECHO.

REM Navigate to project root (one level up from TO RUN\)
cd /d "%~dp0\.."
ECHO Working directory: %CD%

REM 1. Ensure virtual environment exists
IF NOT EXIST "venv\Scripts\python.exe" (
    ECHO ERROR: Python virtual environment not found.
    ECHO Please run "01_install_deps.bat" first.
    EXIT /B 1
)

REM 2. Activate venv
ECHO [1/3] Activating Python virtual environment...
call "venv\Scripts\activate.bat"

REM 3. Download and bundle models via packaging/bundle_models.py
ECHO.
ECHO [2/3] Downloading and bundling models...
ECHO     - Sentence embedder (MiniLM-L6-v2)
ECHO     - NLLB-200 translation model
ECHO     - Ollama formatter model: translategemma:4b
ECHO     - Ollama rewriter model: llama3.2:3b
ECHO.

python "packaging\bundle_models.py"
IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    ECHO WARNING: Model download encountered errors.
    ECHO   - See the Python error messages above for details.
    ECHO   - Common causes:
    ECHO       * No internet or unstable connection
    ECHO       * Hugging Face ^(huggingface.co^) blocked by firewall/VPN
    ECHO       * Corporate proxy requiring extra configuration
    ECHO   - If you are offline, you can:
    ECHO       * Manually download the models on another machine and copy them to:
    ECHO             packaging\hub_models\          ^(MiniLM^)
    ECHO             packaging\hub_models\nllb\     ^(NLLB-200^)
    ECHO       * Then re-run this script.
    ECHO.
    ECHO The hub can still run once these folders contain valid models.
    EXIT /B 1
)

ECHO.
ECHO [3/3] Model bundle completed successfully.
ECHO Models are stored under:
ECHO   - packaging\hub_models\
ECHO   - packaging\ollama_portable\

ECHO.
ECHO ========================================================
ECHO   Model download complete.
ECHO   Next: Run "start_hub.vbs" (or double-click start_hub) to start the Hub.
ECHO ========================================================
ECHO.


