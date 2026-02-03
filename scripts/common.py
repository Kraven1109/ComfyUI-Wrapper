"""Common utilities for ComfyUI workspace management scripts."""

from __future__ import annotations

import os
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
