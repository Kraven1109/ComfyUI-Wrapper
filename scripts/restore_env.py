#!/usr/bin/env python3
"""Restore workspace environment from latest or specified platform backup."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from common import (
    Log,
    get_backups_dir,
    get_platform_env_dir,
    get_platform_key,
    get_workspace_dir,
    rel_path,
    run_uv_sync,
    verify_pytorch,
)


def _find_latest_lock_backup(backups_dir: Path, plat: str) -> Path | None:
    """Return the most recent platform-scoped (or legacy) uv.lock.backup_* file."""
    for pattern in (f"uv.lock.{plat}.backup_2*", "uv.lock.backup_2*"):
        candidates = sorted(
            backups_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]

    for alias_name in (f"uv.lock.{plat}.backup_latest", "uv.lock.backup_latest"):
        alias = backups_dir / alias_name
        if alias.exists():
            return alias
    return None


def restore_env(backup_lock: str | None = None) -> None:
    """Restore environment from specified backup, latest backup, or current uv.lock."""
    workspace_dir = get_workspace_dir()
    backups_dir = get_backups_dir()
    platform_env_dir = get_platform_env_dir()
    plat = get_platform_key()
    lock_file = platform_env_dir / "uv.lock"

    target_backup: Path | None = None

    if backup_lock:
        cand = Path(backup_lock)
        for p in (cand, backups_dir / backup_lock, workspace_dir / backup_lock):
            if p.exists():
                target_backup = p
                break
        if not target_backup:
            Log.error(f"Backup file not found: '{backup_lock}' (checked {rel_path(backups_dir)})")
            sys.exit(1)
    else:
        target_backup = _find_latest_lock_backup(backups_dir, plat)

    if target_backup:
        Log.info(f"Restoring lockfile from backup: {rel_path(target_backup)}")
        shutil.copy2(target_backup, lock_file)
    elif lock_file.exists():
        Log.note(f"No backup archive found in {rel_path(backups_dir)}; syncing from current {rel_path(lock_file)}")
    else:
        Log.error("Neither a backup lockfile nor an active uv.lock was found.")
        sys.exit(1)

    if not run_uv_sync(platform_env_dir, frozen=True):
        sys.exit(1)

    print()
    Log.ok("Environment restored successfully!\n")
    verify_pytorch()


if __name__ == "__main__":
    restore_env(sys.argv[1] if len(sys.argv) > 1 else None)