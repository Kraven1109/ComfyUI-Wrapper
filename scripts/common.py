"""Common utilities for ComfyUI workspace management scripts."""

from __future__ import annotations

import os
import platform
import sys
from datetime import datetime
from pathlib import Path


def get_workspace_dir() -> Path:
    """Get the workspace root directory."""
    script_dir = Path(__file__).parent
    return script_dir.parent.resolve()


def get_comfyui_dir() -> Path:
    """Get the ComfyUI directory."""
    return get_workspace_dir() / "ComfyUI"


def get_timestamp() -> str:
    """Get current timestamp in YYYYMMDD_HHMMSS format."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def verify_pytorch() -> None:
    """Print PyTorch version information."""
    comfyui_dir = get_comfyui_dir()
    sys.path.insert(0, str(comfyui_dir))
    
    try:
        import torch
        print(f"PyTorch: {torch.__version__}")
        print(f"CUDA: {torch.version.cuda}")
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("PyTorch not installed", file=sys.stderr)
        sys.exit(1)


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32" or os.name == "nt"


def get_platform_env_dir() -> Path:
    """Get the platform-specific environment directory (envs/windows or envs/linux)."""
    system = platform.system()
    workspace_dir = get_workspace_dir()
    
    if system == "Windows":
        return workspace_dir / "envs" / "windows"
    else:  # Linux, Darwin (macOS), etc.
        return workspace_dir / "envs" / "linux"


def get_venv_dir() -> Path:
    """Get the active virtual environment directory.
    
    Reads UV_PROJECT_ENVIRONMENT first (set by comfy.sh / comfy.bat), then
    falls back to the conventional .venv path inside the platform env dir.
    """
    uv_project_env = os.environ.get("UV_PROJECT_ENVIRONMENT")
    if uv_project_env:
        return Path(uv_project_env)
    return get_platform_env_dir() / ".venv"


def get_uv_cache_dir() -> Path:
    """Get the uv cache directory."""
    # Check if UV_CACHE_DIR environment variable is set
    if "UV_CACHE_DIR" in os.environ:
        return Path(os.environ["UV_CACHE_DIR"])
    
    # Default locations based on OS
    if is_windows():
        return Path("D:\\.cache_uv")
    else:
        return Path.home() / ".cache" / "uv"
