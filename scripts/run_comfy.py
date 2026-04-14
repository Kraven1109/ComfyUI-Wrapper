#!/usr/bin/env python3
"""Run ComfyUI with workspace environment and optional attention mode."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from common import get_comfyui_dir, get_platform_env_dir, get_workspace_dir


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
    platform_env_dir = get_platform_env_dir()
    
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
    
    # Derive the venv from the active Python executable — always correct regardless of env var
    # state. `uv run` can unset UV_PROJECT_ENVIRONMENT before spawning Python, and a prior
    # shell session (e.g. running llm-serve first) may leave a stale value in the environment.
    # sys.executable = /path/.venv/bin/python  →  venv_path = /path/.venv
    venv_path = Path(sys.executable).parent.parent
    python_exe = Path(sys.executable)

    cmd = [str(python_exe), str(main_py)]
    if attn_flag:
        cmd.append(attn_flag)
    cmd.extend(extra_args)

    # Set PYTHONPATH
    env = os.environ.copy()

    # Propagate the correct venv to all child processes so tools like
    # ComfyUI-Manager's `uv pip install` always target the right environment,
    # overriding any stale values inherited from the outer shell (e.g. after
    # running llm-serve which sets UV_PYTHON and UV_PROJECT_ENVIRONMENT).
    env["VIRTUAL_ENV"] = str(venv_path)
    env["UV_PROJECT_ENVIRONMENT"] = str(venv_path)
    # UV_PYTHON takes precedence over VIRTUAL_ENV/UV_PROJECT_ENVIRONMENT in uv;
    # remove it so child uv commands use the environment we explicitly set above.
    env.pop("UV_PYTHON", None)

    pythonpath = str(comfyui_dir)
    if "PYTHONPATH" in env:
        pythonpath = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONPATH"] = pythonpath
    
    print("[*] Starting ComfyUI...")
    print(f"   Mode: {attn_mode}")
    if attn_flag:
        print(f"   Flag: {attn_flag}")
    print(f"   Venv: {venv_path}")
    print()
    
    # Run ComfyUI
    result = subprocess.run(cmd, cwd=workspace_dir, env=env)
    
    # After ComfyUI exits, auto-lock the environment to capture any Manager changes
    print("\n[*] Auto-locking environment state...")
    try:
        lock_result = subprocess.run(
            ["uv", "lock"],
            cwd=platform_env_dir,  # Run in platform-specific dir
            capture_output=True,
            text=True,
        )
        if lock_result.returncode == 0:
            print("[OK] Environment locked successfully")
            print(f"  (Changes saved to {platform_env_dir.relative_to(workspace_dir)}/uv.lock)")
        else:
            print(f"[WARN] Lock failed: {lock_result.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] Auto-lock error: {e}", file=sys.stderr)
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    run_comfy(sys.argv[1:])
