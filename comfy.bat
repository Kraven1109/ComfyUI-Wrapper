@echo off
REM ComfyUI Workspace Unified CLI
REM Windows uses envs/windows/.venv

set ENV_DIR=envs\windows
set UV_PROJECT_ENVIRONMENT=%~dp0%ENV_DIR%\.venv
set UV_CACHE_DIR=D:\.cache_uv

echo Using environment: %ENV_DIR%
echo Cache dir: %UV_CACHE_DIR%

cd /d "%~dp0"
cd %ENV_DIR% && uv run python "..\..\scripts\cli.py" %*
