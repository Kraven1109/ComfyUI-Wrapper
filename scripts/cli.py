#!/usr/bin/env python3
"""Unified CLI for ComfyUI workspace management."""

from __future__ import annotations

import sys

from backup_env import backup_env
from restore_env import restore_env
from run_comfy import run_comfy
from sync_wrapper import sync_wrapper
from update_comfy import update_comfy


def show_help() -> None:
    """Display help message."""
    help_text = """
ComfyUI Workspace CLI

Usage: comfy <command> [args...]

Commands:
  run [mode] [args...]     Run ComfyUI
                           Modes: sage, flash, pytorch, split, quad, none
                           Default: sage
  
  update                   Update ComfyUI and sync environment
  
  backup                   Backup current environment
  
  restore [backup]         Restore environment
                           backup: Optional backup file (e.g., uv.lock.backup_*)
  
  sync                     Sync wrapper from config + upstream
                           (automatically runs uv lock && uv sync)
  
  help                     Show this help message

Examples:
  comfy run sage                    # Run with SageAttention
  comfy run flash --listen 0.0.0.0  # Run with FlashAttention on all interfaces
  comfy update                      # Update everything
  comfy backup                      # Create backup
  comfy restore                     # Restore from latest
  comfy sync                        # Regenerate wrapper and sync

Configuration:
  Edit wrapper_config.toml to customize PyTorch version and dependencies
  Then run: comfy sync
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
        if command in ("run", "r"):
            run_comfy(args)
        elif command in ("update", "u"):
            update_comfy()
        elif command in ("backup", "b"):
            backup_env()
        elif command in ("restore", "r"):
            restore_arg = args[0] if args else None
            restore_env(restore_arg)
        elif command in ("sync", "s"):
            sync_wrapper()
        elif command in ("help", "h", "-h", "--help"):
            show_help()
        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            print("Run 'comfy help' for usage information.", file=sys.stderr)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
