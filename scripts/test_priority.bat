@echo off
rem Priority: values from the config file win over the command line
cd /d "%~dp0.."

echo.
echo ===== 1. the file sets vfs and script: both values come from the file
call .\run.bat --vfs examples/vfs/minimal.xml --script examples/start_a.txt --config examples/config_full.yaml
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 2. the file sets only vfs: vfs from the file, script from the command line
call .\run.bat --vfs examples/vfs/minimal.xml --script examples/start_a.txt --config examples/config_vfs_only.yaml
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 3. --help describes all parameters
call .\run.bat --help
echo [exit code: %ERRORLEVEL%]

echo.
pause
