@echo off
REM Windows first-time sync from workspace

set "WORKSPACE_DIR=%~dp0"
cd /d "%WORKSPACE_DIR%"

echo ========================================
echo  ComfyUI Windows Environment Sync
echo ========================================
echo.

if not exist "uv.lock" (
    echo ERROR: uv.lock not found!
    echo.
    echo Make sure the workspace is accessible from Windows.
    pause
    exit /b 1
)

echo Syncing from uv.lock...
uv sync

if errorlevel 1 (
    echo.
    echo ERROR: Failed to sync!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Verifying installation...
echo ========================================
echo.
uv run python "%~dp0scripts\common.py" -c "from common import verify_pytorch; verify_pytorch()"

echo.
echo ========================================
echo  Environment Sync Complete!
echo ========================================
echo.
echo You can now run ComfyUI with:
echo   run_comfy.bat sage
echo.
pause
