#!/usr/bin/env python3
"""Safe ComfyUI update script using workspace-level uv lock."""

from __future__ import annotations

import subprocess
import sys

from backup_env import backup_env
from common import get_comfyui_dir, get_workspace_dir, verify_pytorch
from sync_wrapper import sync_wrapper


def update_comfy() -> None:
    """Update ComfyUI and sync environment."""
    workspace_dir = get_workspace_dir()
    comfyui_dir = get_comfyui_dir()
    
    if not comfyui_dir.exists():
        print(f"Error: ComfyUI directory not found: {comfyui_dir}", file=sys.stderr)
        sys.exit(1)
    
    print("📦 Backing up environment before update...")
    backup_env()
    
    print()
    print("🔄 Updating ComfyUI...")
    
    # Reset and pull ComfyUI
    commands = [
        ["git", "reset", "--hard", "HEAD"],
        ["git", "checkout", "master"],
        ["git", "pull", "origin", "master"],
    ]
    
    for cmd in commands:
        result = subprocess.run(cmd, cwd=comfyui_dir, check=False)
        if result.returncode != 0:
            print(f"Error: Command failed: {' '.join(cmd)}", file=sys.stderr)
            sys.exit(1)
    
    print()
    print("🔄 Syncing wrapper with updated ComfyUI/requirements.txt...")
    sync_wrapper()
    
    print()
    print("📥 Syncing workspace environment...")
    result = subprocess.run(["uv", "sync"], cwd=workspace_dir, check=False)
    if result.returncode != 0:
        print("Error: uv sync failed", file=sys.stderr)
        sys.exit(1)
    
    print()
    print("✓ Update complete!")
    print()
    
    verify_pytorch()


if __name__ == "__main__":
    update_comfy()
