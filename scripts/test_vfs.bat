@echo off
rem Loads the three kinds of VFS and shows each one with the command vfs-info
cd /d "%~dp0.."

echo.
echo ===== 1. minimal VFS (only the root folder)
call .\run.bat --vfs examples/vfs/minimal.xml --script examples/show_vfs.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 2. several files in one folder (text and base64)
call .\run.bat --vfs examples/vfs/files.xml --script examples/show_vfs.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 3. three and more levels of folders and files
call .\run.bat --vfs examples/vfs/sample.xml --script examples/show_vfs.txt
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 4. VFS from the config file (it replaces the --vfs value)
call .\run.bat --vfs examples/vfs/minimal.xml --script examples/show_vfs.txt --config examples/config_vfs_only.yaml
echo [exit code: %ERRORLEVEL%]

echo.
echo ===== 5. no VFS at all
call .\run.bat --script examples/show_vfs.txt
echo [exit code: %ERRORLEVEL%]

echo.
pause
