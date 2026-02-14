#!/usr/bin/env python3
"""Backup workspace environment."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from common import get_platform_env_dir, get_timestamp, get_workspace_dir, verify_pytorch


def backup_env() -> None:
    """Create backup of current environment."""
    workspace_dir = get_workspace_dir()
    platform_env_dir = get_platform_env_dir()
    timestamp = get_timestamp()
    
    lock_file = platform_env_dir / "uv.lock"
    if not lock_file.exists():
        print(f"Error: {lock_file} not found", file=sys.stderr)
        sys.exit(1)
    
    print("[*] Creating environment backup...")
    
    # Backup lock file to workspace root
    backup_lock = workspace_dir / f"uv.lock.backup_{timestamp}"
    shutil.copy2(lock_file, backup_lock)
    
    # Export installed packages
    backup_file = workspace_dir / f"env_backup_{timestamp}.txt"
    result = subprocess.run(
        ["uv", "pip", "freeze"],
        cwd=platform_env_dir,  # Run in platform-specific dir
        capture_output=True,
        text=True,
        check=False,
    )
    
    if result.returncode != 0:
        print("Warning: uv pip freeze failed", file=sys.stderr)
    else:
        backup_file.write_text(result.stdout, encoding="utf-8")
        
        # Update latest backup link
        latest_backup = workspace_dir / "env_backup_latest.txt"
        shutil.copy2(backup_file, latest_backup)
    
    print()
    print("[OK] Environment backed up!")
    print(f"   Platform: {platform_env_dir.relative_to(workspace_dir)}")
    print(f"   Package list: {backup_file.name}")
    print(f"   Lock file: {backup_lock.name}")
    if result.returncode == 0:
        package_count = len(result.stdout.strip().split("\n"))
        print(f"   Packages: {package_count}")
    print()
    
    verify_pytorch()


if __name__ == "__main__":
    backup_env()
