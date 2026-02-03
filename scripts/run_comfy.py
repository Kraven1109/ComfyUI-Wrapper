#!/usr/bin/env python3
"""Run ComfyUI with workspace environment and optional attention mode."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from common import get_comfyui_dir, get_workspace_dir


ATTENTION_MODES = {
    "flash": "--use-flash-attention",
    "sage": "--use-sage-attention",
    "split": "--use-split-cross-attention",
    "quad": "--use-quad-cross-attention",
    "pytorch": "--use-pytorch-cross-attention",
    "none": "",
}


def run_comfy(args: list[str]) -> None:
    """Run ComfyUI with specified arguments."""
    workspace_dir = get_workspace_dir()
    comfyui_dir = get_comfyui_dir()
    
    if not comfyui_dir.exists():
        print(f"Error: ComfyUI directory not found: {comfyui_dir}", file=sys.stderr)
        sys.exit(1)
    
    main_py = comfyui_dir / "main.py"
    if not main_py.exists():
        print(f"Error: main.py not found: {main_py}", file=sys.stderr)
        sys.exit(1)
    
    # Parse attention mode
    attn_mode = args[0] if args else "sage"
    extra_args = args[1:] if len(args) > 1 else []
    
    attn_flag = ATTENTION_MODES.get(attn_mode)
    if attn_flag is None:
        print(f"Error: Unknown attention mode: {attn_mode}", file=sys.stderr)
        print(f"Valid modes: {', '.join(ATTENTION_MODES.keys())}", file=sys.stderr)
        sys.exit(1)
    
    # Build command with uv run
    cmd = ["uv", "run", "python", str(main_py)]
    if attn_flag:
        cmd.append(attn_flag)
    cmd.extend(extra_args)
    
    # Set PYTHONPATH
    env = os.environ.copy()
    pythonpath = str(comfyui_dir)
    if "PYTHONPATH" in env:
        pythonpath = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONPATH"] = pythonpath
    
    print("🚀 Starting ComfyUI...")
    print(f"   Mode: {attn_mode}")
    if attn_flag:
        print(f"   Flag: {attn_flag}")
    print()
    
    # Run ComfyUI
    result = subprocess.run(cmd, cwd=workspace_dir, env=env)
    
    # After ComfyUI exits, auto-lock the environment to capture any Manager changes
    print("\n🔒 Auto-locking environment state...")
    try:
        lock_result = subprocess.run(
            ["uv", "lock"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
        )
        if lock_result.returncode == 0:
            print("✓ Environment locked successfully")
            print("  (All ComfyUI-Manager changes are now captured)")
        else:
            print(f"⚠ Lock failed: {lock_result.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Auto-lock error: {e}", file=sys.stderr)
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    run_comfy(sys.argv[1:])
