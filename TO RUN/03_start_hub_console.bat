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

TITLE ResKiosk - Start Hub (Console)
CLS

ECHO ========================================================
ECHO   ResKiosk - Hub (Console Mode)
ECHO ========================================================
ECHO.

REM Navigate to project root (one level up from TO RUN\)
cd /d "%~dp0\.."
ECHO Working directory: %CD%
ECHO.

ECHO Starting hub in background (hidden) via start_hub.vbs...
ECHO This window will now show live logs from hub.log.
ECHO Closing this window will NOT stop the hub.
ECHO.

REM Call the background launcher (hidden hub process)
wscript "%~dp0start_hub.vbs"

REM Tail the hub log so the user can see what's happening
IF EXIST "hub.log" (
    ECHO Showing live hub.log output. Press Ctrl+C to stop watching.
    ECHO The hub will keep running in the background.
    ECHO.
    powershell -NoLogo -Command "Get-Content -Path 'hub.log' -Wait -Tail 50"
) ELSE (
    ECHO hub.log not found yet. The hub may still be starting.
    ECHO Once the hub is running, logs will be written to hub.log.
)

ECHO.
ECHO Log view has ended. The hub process (started by start_hub.vbs) will continue running.
ECHO You can now close this window.
ENDLOCAL

