"""Common utilities, unified logging, git/uv runners, and DRY helpers for ComfyUI workspace."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class Log:
    """Unified ANSI terminal logger across all workspace tools."""

    _COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    @classmethod
    def _wrap(cls, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if cls._COLOR else text

    @classmethod
    def info(cls, msg: str) -> None:
        print(f"{cls._wrap('36;1', '[*]')} {msg}")

    @classmethod
    def ok(cls, msg: str) -> None:
        print(f"{cls._wrap('32;1', '[OK]')} {msg}")

    @classmethod
    def note(cls, msg: str) -> None:
        print(f"{cls._wrap('34;1', '[NOTE]')} {msg}")

    @classmethod
    def clean(cls, msg: str) -> None:
        print(f"{cls._wrap('35;1', '[CLEAN]')} {msg}")

    @classmethod
    def warn(cls, msg: str) -> None:
        print(f"{cls._wrap('33;1', '[WARN]')} {msg}", file=sys.stderr)

    @classmethod
    def error(cls, msg: str) -> None:
        print(f"{cls._wrap('31;1', '[ERROR]')} {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Path & Platform Helpers (Single Source of Truth)
# ---------------------------------------------------------------------------
def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32" or os.name == "nt"


def get_platform_key() -> str:
    """Return canonical lowercase platform identifier ('windows' or 'linux')."""
    return "windows" if is_windows() else "linux"


def get_workspace_dir() -> Path:
    """Get the workspace root directory."""
    return Path(__file__).resolve().parent.parent


def get_comfyui_dir() -> Path:
    """Get the ComfyUI directory."""
    return get_workspace_dir() / "ComfyUI"


def rel_path(path: Path) -> Path:
    """Return path relative to workspace_dir if possible, otherwise original path."""
    ws = get_workspace_dir()
    return path.relative_to(ws) if path.is_relative_to(ws) else path


def get_timestamp() -> str:
    """Get current timestamp in YYYYMMDD_HHMMSS format."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_platform_env_dir() -> Path:
    """Get the platform-specific environment directory (envs/windows or envs/linux)."""
    return get_workspace_dir() / "envs" / get_platform_key()


def get_venv_dir() -> Path:
    """Get the active virtual environment directory."""
    if uv_env := os.environ.get("UV_PROJECT_ENVIRONMENT"):
        return Path(uv_env)
    return get_platform_env_dir() / ".venv"


def get_venv_python(venv_dir: Path | None = None) -> Path:
    """Resolve the Python executable inside the target venv with fallback to sys.executable."""
    target_venv = venv_dir or get_venv_dir()
    candidate = target_venv / ("Scripts/python.exe" if is_windows() else "bin/python")
    return candidate if candidate.exists() else Path(sys.executable)


def get_clean_uv_env(venv_dir: Path | None = None) -> dict[str, str]:
    """Return an environment dictionary sanitized against outer-shell UV_PYTHON leaks."""
    env = os.environ.copy()
    target_venv = str(venv_dir or get_venv_dir())
    env["VIRTUAL_ENV"] = target_venv
    env["UV_PROJECT_ENVIRONMENT"] = target_venv
    env.pop("UV_PYTHON", None)
    return env


def get_uv_cache_dir() -> Path:
    """Get the uv cache directory."""
    if "UV_CACHE_DIR" in os.environ:
        return Path(os.environ["UV_CACHE_DIR"])
    return Path("D:\\.cache_uv") if is_windows() else Path.home() / ".cache" / "uv"


def _ensure_dir(name: str) -> Path:
    d = get_workspace_dir() / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_backups_dir() -> Path:
    return _ensure_dir("backups")


def get_logs_dir() -> Path:
    return _ensure_dir("logs")


# ---------------------------------------------------------------------------
# DRY File & CLI Utilities
# ---------------------------------------------------------------------------
def read_clean_lines(path: Path, ignore_prefixes: tuple[str, ...] = ()) -> list[str]:
    """Read UTF-8 file, strip inline '#' comments and whitespace, and skip matching prefixes."""
    if not path.is_file():
        return []
    items: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or (ignore_prefixes and line.startswith(ignore_prefixes)):
            continue
        items.append(line)
    return items


def confirm_action(prompt: str, abort_msg: str = "Launch aborted.") -> bool:
    """Unified interactive TTY prompt with safe Ctrl+C/EOF handling."""
    if not sys.stdin.isatty():
        Log.error(f"Non-interactive shell cannot confirm prompt. {abort_msg}")
        sys.exit(1)
    try:
        ans = input(f"[?] {prompt} [y/N]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n[*] Aborted.")
        sys.exit(0)
    return ans in ("y", "yes")


def prune_files(
    directory: Path,
    patterns: tuple[str, ...] = ("*",),
    max_days: int | None = None,
    keep_last: int | None = None,
) -> int:
    """Unified file pruner supporting both age-based (max_days) and count-based (keep_last) rotation."""
    if not directory.exists():
        return 0

    now_ts = datetime.now().timestamp()
    cutoff_seconds = (max_days * 86400) if max_days is not None else None
    deleted = 0

    for pattern in patterns:
        matched = [p for p in directory.glob(pattern) if p.is_file()]
        matched.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        for idx, file_path in enumerate(matched):
            should_delete = False
            if keep_last is not None and idx >= keep_last:
                should_delete = True
            elif cutoff_seconds is not None:
                try:
                    if (now_ts - file_path.stat().st_mtime) > cutoff_seconds:
                        should_delete = True
                except OSError:
                    pass

            if should_delete:
                try:
                    file_path.unlink()
                    deleted += 1
                except OSError:
                    pass
    return deleted


def rotate_logs(max_days: int = 30) -> int:
    """Rotate and delete logs older than max_days in the logs directory."""
    return prune_files(get_logs_dir(), patterns=("*.log", "*.txt"), max_days=max_days)


# ---------------------------------------------------------------------------
# Consolidated Git & UV Subprocess Runners
# ---------------------------------------------------------------------------
def has_git() -> bool:
    return shutil.which("git") is not None


def run_git(
    args: list[str],
    cwd: Path,
    capture: bool = True,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Consolidated git command runner."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=capture,
        text=True,
        check=check,
    )


def run_uv_lock(
    platform_dir: Path | None = None,
    venv_dir: Path | None = None,
    skip_if_fresh: bool = False,
    timeout: float = 60.0,
) -> bool:
    """Consolidated uv lock runner with clean env, preview flags, and freshness check."""
    target_dir = platform_dir or get_platform_env_dir()
    lock_file = target_dir / "uv.lock"
    pyproject_file = target_dir / "pyproject.toml"
    wrapper_cfg = get_workspace_dir() / "wrapper_config.toml"

    if skip_if_fresh and lock_file.exists() and pyproject_file.exists():
        lock_mtime = lock_file.stat().st_mtime
        newest_input = max(
            pyproject_file.stat().st_mtime,
            wrapper_cfg.stat().st_mtime if wrapper_cfg.exists() else 0.0,
        )
        if lock_mtime >= newest_input:
            Log.ok("Environment lock is already up-to-date (skipped redundant uv lock).")
            return True

    cmd = ["uv", "lock", "--preview-features", "extra-build-dependencies"]
    try:
        res = subprocess.run(
            cmd,
            cwd=target_dir,
            env=get_clean_uv_env(venv_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if res.returncode == 0:
            if lock_file.exists():
                lock_file.touch()
            Log.ok(f"Environment locked ({rel_path(lock_file)})")
            return True
        Log.error(f"uv lock failed:\n{res.stderr.strip()}")
        return False
    except Exception as e:
        Log.error(f"uv lock execution error: {e}")
        return False


def run_uv_sync(
    platform_dir: Path | None = None,
    venv_dir: Path | None = None,
    frozen: bool = False,
) -> bool:
    """Consolidated uv sync runner with consistent platform and preview flags."""
    target_dir = platform_dir or get_platform_env_dir()
    clean_env = get_clean_uv_env(venv_dir)

    cmd = ["uv", "sync", "--all-extras", "--preview-features", "extra-build-dependencies"]
    if frozen:
        cmd.append("--frozen")
    if target_dir.name.lower() == "linux":
        cmd.extend(["--python-platform", "linux"])

    res = subprocess.run(
        cmd,
        cwd=target_dir,
        env=clean_env,
        capture_output=True,
        text=True,
    )
    if res.returncode == 0:
        Log.ok(f"Environment synced: {clean_env['UV_PROJECT_ENVIRONMENT']}")
        return True

    Log.error(f"uv sync failed:\n{res.stderr.strip()}")
    return False


def verify_pytorch() -> None:
    """Print PyTorch, CUDA, and GPU hardware telemetry."""
    comfyui_dir = get_comfyui_dir()
    if str(comfyui_dir) not in sys.path:
        sys.path.insert(0, str(comfyui_dir))

    try:
        import torch

        Log.info("Hardware & Runtime Verification:")
        print(f"    PyTorch : {torch.__version__}")
        print(f"    CUDA    : {torch.version.cuda or 'N/A'}")
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            arch_list = ", ".join(torch.cuda.get_arch_list())
            print(f"    GPU     : {device_name} ({vram_gb:.1f} GB VRAM)")
            print(f"    Archs   : {arch_list}")
    except ImportError:
        Log.error("PyTorch is not installed in the active environment.")
        sys.exit(1)