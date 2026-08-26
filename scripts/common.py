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


def get_backups_dir() -> Path:
    """Get the backups directory, creating it if it doesn't exist."""
    backups_dir = get_workspace_dir() / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir


def get_logs_dir() -> Path:
    """Get the logs directory, creating it if it doesn't exist."""
    logs_dir = get_workspace_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def rotate_logs(max_days: int = 30) -> int:
    """Rotate and delete logs older than max_days in the logs directory."""
    logs_dir = get_logs_dir()
    now_ts = datetime.now().timestamp()
    cutoff_seconds = max_days * 86400
    deleted_count = 0
    
    for file_path in logs_dir.glob("*"):
        if file_path.is_file() and file_path.suffix in (".log", ".txt"):
            try:
                mtime = file_path.stat().st_mtime
                if (now_ts - mtime) > cutoff_seconds:
                    file_path.unlink()
                    deleted_count += 1
            except Exception:
                pass
    return deleted_count

