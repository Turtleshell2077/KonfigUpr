@echo off
rem Stage 5: rmdir and rm change the VFS only in memory
cd /d "%~dp0.."

echo.
echo ===== 1. the start script with rm and rmdir on the stage 5 VFS
call .\run.bat --vfs examples/vfs/stage5.xml --script examples/stage5.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 2. the same run again: the XML file was not changed, the result is the same
call .\run.bat --vfs examples/vfs/stage5.xml --script examples/stage5.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 3. the same script without VFS (commands report that it is missing)
call .\run.bat --script examples/stage5.txt
echo [exit code: %ERRORLEVEL%]

echo.
pause
