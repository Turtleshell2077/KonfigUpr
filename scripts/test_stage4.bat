@echo off
rem Stage 4: the start script with ls, cd, tac, rev and whoami
cd /d "%~dp0.."

echo.
echo ===== 1. all modes of the commands on the sample VFS
call .\run.bat --vfs examples/vfs/sample.xml --script examples/stage4.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 2. the same script, the VFS comes from the config file
call .\run.bat --script examples/stage4.txt --config examples/config_vfs_only.yaml
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 3. the same script without VFS (commands report that it is missing)
call .\run.bat --script examples/stage4.txt
echo [exit code: %ERRORLEVEL%]

echo.
pause
