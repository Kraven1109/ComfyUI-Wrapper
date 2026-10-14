#!/usr/bin/env python3
"""ComfyUI Workspace Architecture Visualization."""

from __future__ import annotations


def show_structure() -> None:
    """Display workspace structure with up-to-date annotations."""
    structure = """\
╔═══════════════════════════════════════════════════════════════════════╗
║  ComfyUI Portable Workspace - SoTA Unified Architecture               ║
╚═══════════════════════════════════════════════════════════════════════╝

📁 ComfyUI_portable/
│
├─ 🎯 UNIFIED CLI ENTRYPOINTS
│  ├─ comfy.sh                      Linux/macOS: ./comfy.sh <command>
│  └─ comfy.bat                     Windows:     comfy.bat <command>
│
│     Commands:
│       comfy run, r [mode] [args]  Launch ComfyUI (default: sage)
│       comfy update, u             Backup + revert patches + git pull + sync
│       comfy sync, s               Generate pyproject.toml + uv lock & sync + patches
│       comfy patch, p [action]     Manage patches (sync | status | revert)
│       comfy backup, b             Snapshot platform uv.lock & frozen package list
│       comfy restore, res [file]   Rollback environment to latest/target backup
│       comfy doctor, d             Verify PyTorch, CUDA, VRAM & GPU architectures
│       comfy structure, st         Show workspace architecture diagram
│       comfy help, h               Show command reference
│
├─ 📝 wrapper_config.toml           ← SINGLE SOURCE OF CONFIGURATION
│  ├─ [pytorch]                     (CUDA index URLs & wheel sources)
│  ├─ [dependencies]                (custom, windows, and linux packages)
│  └─ [uv.extra_build_deps]         (build-time dependencies for source wheels)
│
├─ 🌍 envs/                         ← ISOLATED PLATFORM ENVIRONMENTS
│  ├─ windows/                      (pyproject.toml, uv.lock, .venv/)
│  └─ linux/                        (pyproject.toml, uv.lock, .venv/)
│
├─ 🩹 patches/                      ← NON-INTRUSIVE PATCH SYSTEM
│  ├─ patches.txt                   (optional manifest controlling active patches)
│  ├─ <ext_name>/__init__.py        (Category A: Auto-linked to custom_nodes/)
│  └─ <target>/*.patch              (Category B: Idempotent git apply diffs)
│
├─ 🐍 scripts/                      ← CONSOLIDATED CORE ENGINE
│  ├─ common.py                     (Log, paths, git/uv runners, pruner, TTY prompt)
│  ├─ cli.py                        (unified command dispatcher)
│  ├─ run_comfy.py                  (smart port/VRAM manager + ECMA-48 tee logger)
│  ├─ sync_wrapper.py               (idempotent TOML generator + env sync)
│  ├─ update_comfy.py               (safe upstream git updater + changelog)
│  ├─ patch_manager.py              (Category A links + Category B git patches)
│  ├─ backup_env.py                 (platform-scoped lock & freeze snapshot)
│  ├─ restore_env.py                (platform-aware rollback from backups/)
│  └─ show_structure.py             (architecture overview)
│
├─ 💾 backups/                      ← PLATFORM-ISOLATED SNAPSHOTS (KEEP LAST 20)
│  ├─ uv.lock.<plat>.backup_*       (exact per-OS lockfile states)
│  └─ env_backup.<plat>_*.txt       (frozen per-OS package inventories)
│
├─ 📜 logs/                         ← SESSION LOGS (30-DAY AUTO-ROTATION)
│  └─ comfyui_YYYYMMDD_HHMMSS.log   (clean ANSI-stripped console output)
│
└─ 📂 ComfyUI/                      ← UPSTREAM GIT REPOSITORY
   ├─ pyproject.toml & requirements.txt
   ├─ custom_nodes/                 (hosts Category A links & custom nodes)
   └─ main.py
"""
    print(structure)


if __name__ == "__main__":
    show_structure()