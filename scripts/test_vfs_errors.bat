@echo off
rem VFS loading errors, and then the three correct VFS still load
cd /d "%~dp0.."

echo.
echo ===== 1. the VFS file does not exist (expected exit code 1)
call .\run.bat --vfs examples/vfs/missing.xml --script examples/show_vfs.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 2. the file is not valid XML (expected exit code 1)
call .\run.bat --vfs examples/vfs/bad_syntax.xml --script examples/show_vfs.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 3. valid XML, but the wrong format (expected exit code 1)
call .\run.bat --vfs examples/vfs/bad_format.xml --script examples/show_vfs.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 4. correct minimal VFS
call .\run.bat --vfs examples/vfs/minimal.xml --script examples/show_vfs.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 5. correct VFS with several files
call .\run.bat --vfs examples/vfs/files.xml --script examples/show_vfs.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 6. correct VFS with three and more levels
call .\run.bat --vfs examples/vfs/sample.xml --script examples/show_vfs.txt
echo [exit code: %ERRORLEVEL%]

echo.
pause
