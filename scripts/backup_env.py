#!/usr/bin/env python3
"""Backup workspace environment with platform-isolated automatic snapshot rotation."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from common import (
    Log,
    get_backups_dir,
    get_clean_uv_env,
    get_platform_env_dir,
    get_platform_key,
    get_timestamp,
    prune_files,
    rel_path,
    verify_pytorch,
)


def _save_snapshot(src_or_content: Path | str, timestamped_dest: Path, latest_dest: Path) -> None:
    """Write or copy snapshot and update its _latest alias atomically."""
    if isinstance(src_or_content, Path):
        shutil.copy2(src_or_content, timestamped_dest)
    else:
        timestamped_dest.write_text(src_or_content, encoding="utf-8")
    shutil.copy2(timestamped_dest, latest_dest)


def backup_env() -> None:
    """Create platform-scoped backup of current environment in backups/ directory."""
    backups_dir = get_backups_dir()
    platform_env_dir = get_platform_env_dir()
    plat = get_platform_key()
    timestamp = get_timestamp()

    lock_file = platform_env_dir / "uv.lock"
    if not lock_file.exists() or lock_file.stat().st_size == 0:
        Log.warn(f"No valid uv.lock found at {rel_path(lock_file)} — skipping lock backup.")
        return

    Log.info(f"Creating {plat} environment backup...")

    backup_lock = backups_dir / f"uv.lock.{plat}.backup_{timestamp}"
    _save_snapshot(lock_file, backup_lock, backups_dir / f"uv.lock.{plat}.backup_latest")

    backup_file = backups_dir / f"env_backup.{plat}_{timestamp}.txt"
    result = subprocess.run(
        ["uv", "pip", "freeze"],
        cwd=platform_env_dir,
        env=get_clean_uv_env(),
        capture_output=True,
        text=True,
    )

    pkg_count = 0
    if result.returncode != 0:
        Log.warn(f"uv pip freeze failed: {result.stderr.strip()}")
    else:
        _save_snapshot(result.stdout, backup_file, backups_dir / f"env_backup.{plat}_latest.txt")
        pkg_count = sum(1 for line in result.stdout.splitlines() if line.strip())

    prune_files(
        backups_dir,
        patterns=(f"uv.lock.{plat}.backup_2*", f"env_backup.{plat}_2*.txt"),
        keep_last=20,
    )

    Log.ok("Environment backed up!")
    print(f"    Platform     : {rel_path(platform_env_dir)}")
    print(f"    Lock Snapshot: {rel_path(backup_lock)}")
    if pkg_count:
        print(f"    Package List : {rel_path(backup_file)} ({pkg_count} packages)")
    print()

    verify_pytorch()


if __name__ == "__main__":
    backup_env()