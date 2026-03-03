@echo off
cd /d "%~dp0"
call "venv\Scripts\activate.bat"
pyinstaller "packaging\reskiosk-hub.spec" --noconfirm
echo.
echo Build complete. Check dist\ResKiosk-Hub\ for the output.
pause
