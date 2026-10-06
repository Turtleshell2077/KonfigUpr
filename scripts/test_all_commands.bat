@echo off
rem Runs the start script with all commands of stages 1-3 on every kind of VFS
cd /d "%~dp0.."

echo.
echo ===== 1. all commands, minimal VFS
call .\run.bat --vfs examples/vfs/minimal.xml --script examples/all_commands.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 2. all commands, several files
call .\run.bat --vfs examples/vfs/files.xml --script examples/all_commands.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 3. all commands, three and more levels
call .\run.bat --vfs examples/vfs/sample.xml --script examples/all_commands.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 4. all commands without VFS (vfs-info reports it)
call .\run.bat --script examples/all_commands.txt
echo [exit code: %ERRORLEVEL%]

echo.
pause
