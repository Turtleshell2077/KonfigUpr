@echo off
setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    py -3 -m src.emulator %*
) else (
    python -m src.emulator %*
)
exit /b %ERRORLEVEL%
