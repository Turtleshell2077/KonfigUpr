@echo off
rem Calls the emulator with every parameter: --vfs, --script, --config, --help
cd /d "%~dp0.."

echo.
echo ===== 1. only --vfs (the input is empty, so the dialog ends at once)
call .\run.bat --vfs examples/vfs/minimal.xml < nul
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 2. only --script
call .\run.bat --script examples/start_a.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 3. only --config (the file sets both vfs and script)
call .\run.bat --config examples/config_full.yaml
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 4. --vfs and --script together
call .\run.bat --vfs examples/vfs/sample.xml --script examples/start_b.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 5. all three parameters (the config sets only vfs)
call .\run.bat --vfs examples/vfs/minimal.xml --script examples/start_a.txt --config examples/config_vfs_only.yaml
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 6. --help
call .\run.bat --help
echo [exit code: %ERRORLEVEL%]

echo.
pause
