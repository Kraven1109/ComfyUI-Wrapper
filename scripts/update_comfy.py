#!/usr/bin/env python3
"""Safe ComfyUI update script using workspace-level uv lock."""

from __future__ import annotations

import subprocess
import sys

from backup_env import backup_env
from common import get_comfyui_dir, get_workspace_dir, verify_pytorch
from patch_manager import sync_dynamic_patches
from sync_wrapper import sync_wrapper


def update_comfy() -> None:
    """Update ComfyUI and sync environment."""
    workspace_dir = get_workspace_dir()
    comfyui_dir = get_comfyui_dir()
    
    if not comfyui_dir.exists():
        print(f"Error: ComfyUI directory not found: {comfyui_dir}", file=sys.stderr)
        sys.exit(1)
    
    print("[*] Backing up environment before update...")
    backup_env()
    
    print()
    print("[*] Updating ComfyUI...")
    
    # Check if ComfyUI is a Git repository before running git commands
    if not (comfyui_dir / ".git").exists():
        print(f"Error: ComfyUI is not a Git repository at: {comfyui_dir}", file=sys.stderr)
        print("Cannot update automatically via git. Please update it manually or clone it using git.", file=sys.stderr)
        sys.exit(1)
        
    # Ensure remote 'origin' exists
    remote_check = subprocess.run(["git", "remote", "get-url", "origin"], cwd=comfyui_dir, capture_output=True, text=True)
    if remote_check.returncode != 0:
        print("[*] Remote 'origin' not found. Adding default ComfyUI remote...")
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/comfyanonymous/ComfyUI.git"], cwd=comfyui_dir)

    print("[*] Fetching latest changes from origin master...")
    fetch_result = subprocess.run(["git", "fetch", "origin", "master"], cwd=comfyui_dir)
    if fetch_result.returncode != 0:
        print("Error: Failed to fetch from origin master", file=sys.stderr)
        sys.exit(1)

    print("[*] Resetting working tree to origin/master...")
    # Checkout master pointing to FETCH_HEAD (works even if HEAD is unborn)
    checkout_result = subprocess.run(["git", "checkout", "-f", "-B", "master", "FETCH_HEAD"], cwd=comfyui_dir)
    if checkout_result.returncode != 0:
        print("Error: Failed to checkout master branch", file=sys.stderr)
        sys.exit(1)

    # Force reset to discard any modifications
    reset_result = subprocess.run(["git", "reset", "--hard", "FETCH_HEAD"], cwd=comfyui_dir)
    if reset_result.returncode != 0:
        print("Error: Failed to reset working tree", file=sys.stderr)
        sys.exit(1)
    
    print()
    print("[*] Syncing wrapper with updated ComfyUI/requirements.txt...")
    sync_wrapper()

    print()
    print("[*] Re-applying dynamic patches after upstream reset...")
    _, conflicts = sync_dynamic_patches(report_conflicts=True)
    if conflicts:
        print(
            f"[WARN] {len(conflicts)} patch(es) entered CONFLICT state after update.",
            file=sys.stderr,
        )
        print("       Run: comfy patch status", file=sys.stderr)

    print()
    print("[OK] Update complete!")
    print()
    
    verify_pytorch()


if __name__ == "__main__":
    update_comfy()
