@echo off
python "%~dp0src\emulator.py" %*
exit /b %ERRORLEVEL%
