@echo off
REM ComfyUI Workspace Unified CLI
REM Windows uses envs/windows/.venv
set ENV_DIR=envs\windows
set UV_PROJECT_ENVIRONMENT=%~dp0%ENV_DIR%\.venv
set VIRTUAL_ENV=%~dp0%ENV_DIR%\.venv
REM UV_PYTHON overrides UV_PROJECT_ENVIRONMENT — unset it so uv uses the correct project env
set UV_PYTHON=
set UV_CACHE_DIR=D:\.cache_uv
echo Using environment: %ENV_DIR%
echo Cache dir: %UV_CACHE_DIR%
if not exist "%UV_CACHE_DIR%" mkdir "%UV_CACHE_DIR%"
set PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] uv not found. Installing...
    powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Install failed. Visit https://docs.astral.sh/uv/getting-started/installation/
        pause
        exit /b 1
    )
    echo [INFO] uv installed. Please re-run this script.
    pause
    exit /b 0
)

REM ── Auto-symlink custom node projects ─────────────────────────────────────
set CUSTOM_NODES_DIR=%~dp0ComfyUI\custom_nodes
if not exist "%CUSTOM_NODES_DIR%" mkdir "%CUSTOM_NODES_DIR%"

call :symlink "ComfyUI-LLama"  "D:\quang_dev\ComfyUI-LLama"
call :symlink "ComfyUI-TTSS"   "D:\quang_dev\comfyUI-TTSS"
REM ──────────────────────────────────────────────────────────────────────────

REM ── Auto-symlink model directories ────────────────────────────────────────
set MODELS_DIR=%~dp0ComfyUI\models
call :symlink_model "LLM" "E:\llm\models"
REM ──────────────────────────────────────────────────────────────────────────

cd /d "%~dp0%ENV_DIR%" && uv run python "..\..\scripts\cli.py" %*
goto :eof

:symlink
set NODE_NAME=%~1
set SRC=%~2
set DEST=%CUSTOM_NODES_DIR%\%NODE_NAME%
if not exist "%SRC%" (
    echo [WARN] Source not found, skipping: %SRC%
) else (
    if exist "%DEST%" rmdir "%DEST%" 2>nul
    if exist "%DEST%" del "%DEST%" 2>nul
    mklink /D "%DEST%" "%SRC%" >nul 2>&1 && echo [OK] Symlinked: %NODE_NAME% ^> %SRC% || echo [WARN] Failed to symlink %NODE_NAME% (try running as Admin)
)
goto :eof

:symlink_model
set MODEL_NAME=%~1
set SRC=%~2
set DEST=%MODELS_DIR%\%MODEL_NAME%
if not exist "%SRC%" (
    echo [WARN] Model source not found, skipping: %SRC%
) else (
    if exist "%DEST%" rmdir "%DEST%" 2>nul
    if exist "%DEST%" del "%DEST%" 2>nul
    mklink /D "%DEST%" "%SRC%" >nul 2>&1 && echo [OK] Model dir symlinked: %MODEL_NAME% ^> %SRC% || echo [WARN] Failed to symlink %MODEL_NAME% (try running as Admin)
)
goto :eof
