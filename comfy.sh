#!/usr/bin/env bash
# ComfyUI Workspace Unified CLI
exec uv run python "$(dirname "$0")/scripts/cli.py" "$@"
