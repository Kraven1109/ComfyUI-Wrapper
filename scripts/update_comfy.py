#!/usr/bin/env python3
"""Safe ComfyUI update script using workspace-level uv lock."""

from __future__ import annotations

import sys
from pathlib import Path

from backup_env import backup_env
from common import Log, get_comfyui_dir, run_git, verify_pytorch
from patch_manager import revert_all_git_patches, sync_dynamic_patches
from sync_wrapper import sync_wrapper


def _get_git_head(repo_dir: Path) -> str:
    res = run_git(["rev-parse", "--short", "HEAD"], cwd=repo_dir)
    return res.stdout.strip() if res.returncode == 0 else "unknown"


def update_comfy() -> None:
    """Update ComfyUI upstream safely, sync dependencies, and re-apply patches."""
    comfyui_dir = get_comfyui_dir()

    if not (comfyui_dir / ".git").exists():
        Log.error(f"ComfyUI is not a valid Git repository at: {comfyui_dir}")
        sys.exit(1)

    Log.info("Step 1/5: Backing up current environment state...")
    backup_env()

    Log.info("Step 2/5: Reverting Category B Git patches cleanly before git pull...")
    revert_all_git_patches()

    Log.info("Step 3/5: Fetching latest upstream changes from origin/master...")
    if run_git(["remote", "get-url", "origin"], cwd=comfyui_dir).returncode != 0:
        Log.note("Remote 'origin' not found. Adding default ComfyUI remote...")
        run_git(
            ["remote", "add", "origin", "https://github.com/comfyanonymous/ComfyUI.git"],
            cwd=comfyui_dir,
            check=True,
        )

    old_head = _get_git_head(comfyui_dir)

    if run_git(["fetch", "origin", "master"], cwd=comfyui_dir, capture=False).returncode != 0:
        Log.error("Failed to fetch from origin/master.")
        sys.exit(1)

    # `checkout -f -B master FETCH_HEAD` atomically resets the branch and working tree
    if run_git(["checkout", "-f", "-B", "master", "FETCH_HEAD"], cwd=comfyui_dir, capture=False).returncode != 0:
        Log.error("Failed to checkout and reset master branch to FETCH_HEAD.")
        sys.exit(1)

    new_head = _get_git_head(comfyui_dir)
    if old_head != new_head and old_head != "unknown":
        Log.ok(f"Updated ComfyUI: {old_head} -> {new_head}")
        log_summary = run_git(["log", "--oneline", "-n", "10", f"{old_head}..{new_head}"], cwd=comfyui_dir)
        if log_summary.stdout.strip():
            print("    Recent upstream commits:")
            for line in log_summary.stdout.strip().splitlines():
                print(f"      • {line}")
    else:
        Log.ok(f"ComfyUI is already at latest commit ({new_head}).")

    print()
    Log.info("Step 4/5: Syncing wrapper dependencies with updated ComfyUI/requirements.txt...")
    sync_wrapper(sync_patches=False)

    print()
    Log.info("Step 5/5: Re-applying dynamic patches...")
    _, conflicts = sync_dynamic_patches(report_conflicts=True)
    if conflicts:
        Log.warn(f"{len(conflicts)} patch(es) entered CONFLICT state after upstream update.")
        Log.warn("Run 'comfy patch status' to inspect affected files.")

    print()
    Log.ok("ComfyUI workspace update complete!\n")
    verify_pytorch()


if __name__ == "__main__":
    update_comfy()