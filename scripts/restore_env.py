#!/usr/bin/env python3
"""Restore workspace environment from backup."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from common import get_platform_env_dir, get_workspace_dir, verify_pytorch


def restore_env(backup_lock: str | None = None) -> None:
    """Restore environment from uv.lock or backup."""
    workspace_dir = get_workspace_dir()
    platform_env_dir = get_platform_env_dir()
    lock_file = platform_env_dir / "uv.lock"
    
    if backup_lock:
        backup_path = workspace_dir / backup_lock
        if not backup_path.exists():
            print(f"Error: Backup file not found: {backup_lock}", file=sys.stderr)
            sys.exit(1)
        
        print(f"[*] Restoring from lockfile: {backup_lock}")
        shutil.copy2(backup_path, lock_file)
    else:
        print(f"[*] Restoring from current {lock_file.relative_to(workspace_dir)}")
    
    # Run uv sync in platform-specific dir
    result = subprocess.run(["uv", "sync"], cwd=platform_env_dir, check=False)
    if result.returncode != 0:
        print("Error: uv sync failed", file=sys.stderr)
        sys.exit(1)
    
    print()
    print("[OK] Environment restored!")
    print()
    
    verify_pytorch()


if __name__ == "__main__":
    backup_arg = sys.argv[1] if len(sys.argv) > 1 else None
    restore_env(backup_arg)
