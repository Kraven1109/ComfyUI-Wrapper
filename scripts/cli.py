#!/usr/bin/env python3
"""Unified CLI for ComfyUI workspace management."""

from __future__ import annotations

import sys

from backup_env import backup_env
from common import Log, verify_pytorch
from patch_manager import handle_patch_cli
from restore_env import restore_env
from run_comfy import run_comfy
from show_structure import show_structure
from sync_wrapper import sync_wrapper
from update_comfy import update_comfy


def show_help() -> None:
    """Display help message."""
    help_text = """\
ComfyUI Workspace CLI

Usage: comfy <command> [args...]

Commands:
  run, r [mode] [args...]    Run ComfyUI (default mode: sage)
                             Modes: sage, flash, pytorch, split, quad, none
  update, u                  Update ComfyUI upstream, sync env, and re-apply patches
  sync, s                    Generate platform pyproject.toml, uv lock & sync, and patches
  backup, b                  Backup current platform environment lock state
  restore, res [backup]      Restore environment from latest or specified backup
  patch, p [action]          Manage dynamic patches (actions: sync, status, revert)
  doctor, d                  Verify PyTorch, CUDA, and GPU environment status
  structure, st              Show workspace architecture diagram
  help, h                    Show this help message

Examples:
  comfy run                         # Run with default SageAttention
  comfy run --port 8189             # Run with SageAttention on port 8189
  comfy run flash --listen 0.0.0.0  # Run with FlashAttention on all interfaces
  comfy update                      # Full backup + git update + uv sync + patch sync
  comfy sync                        # Regenerate wrapper & sync packages
  comfy patch status                # Inspect all Category A & B patches
  comfy restore                     # Rollback to latest platform environment backup
  comfy structure                   # Display workspace layout & command map
"""
    print(help_text)


def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    try:
        match command:
            case "run" | "r":
                run_comfy(args)
            case "update" | "u":
                update_comfy()
            case "backup" | "b":
                backup_env()
            case "restore" | "res":
                restore_env(args[0] if args else None)
            case "sync" | "s":
                sync_wrapper()
            case "patch" | "p":
                handle_patch_cli(args)
            case "doctor" | "d":
                verify_pytorch()
            case "structure" | "st":
                show_structure()
            case "help" | "h" | "-h" | "--help":
                show_help()
            case _:
                Log.error(f"Unknown command: '{command}'")
                Log.info("Run 'comfy help' for usage information.")
                sys.exit(1)
    except KeyboardInterrupt:
        print("\n", file=sys.stderr)
        Log.warn("Interrupted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()