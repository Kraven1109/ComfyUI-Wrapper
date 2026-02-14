#!/usr/bin/env bash
# ComfyUI Workspace Unified CLI
# Linux/macOS uses envs/linux/.venv

ENV_DIR="envs/linux"
export UV_PROJECT_ENVIRONMENT="$(dirname "$0")/$ENV_DIR/.venv"
export UV_CACHE_DIR="/run/media/quangtm/DATA1/.cache_uv"

echo "Using environment: $ENV_DIR"
echo "Cache dir: $UV_CACHE_DIR"

# Create cache directory if it doesn't exist
mkdir -p "$UV_CACHE_DIR"

# Change to env directory and run with relative paths
WORKSPACE_DIR="$(dirname "$0")"
cd "$WORKSPACE_DIR/$ENV_DIR" && exec uv run python "../../scripts/cli.py" "$@"
