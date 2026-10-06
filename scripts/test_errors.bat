@echo off
rem Errors: bad config, missing script, wrong parameter
cd /d "%~dp0.."

echo.
echo ===== 1. the config file does not exist (expected exit code 1)
call .\run.bat --vfs examples/vfs/sample.xml --script examples/start_a.txt --config examples/missing.yaml
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 2. the config is not valid YAML (expected exit code 1)
call .\run.bat --vfs examples/vfs/sample.xml --script examples/start_a.txt --config examples/config_bad_syntax.yaml
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 3. the start script does not exist (expected exit code 1)
call .\run.bat --vfs examples/vfs/sample.xml --script examples/missing.txt --config examples/config_vfs_only.yaml
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 4. an unknown parameter (expected exit code 2)
call .\run.bat --vfs examples/vfs/sample.xml --script examples/start_a.txt --config examples/config_full.yaml --unknown
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 5. --help
call .\run.bat --help
echo [exit code: %ERRORLEVEL%]

echo.
pause
