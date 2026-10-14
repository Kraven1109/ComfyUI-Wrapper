#!/usr/bin/env python3
"""Run ComfyUI with workspace environment, smart lifecycle management, and attention modes."""

from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import TextIO

from common import (
    Log,
    confirm_action,
    get_clean_uv_env,
    get_comfyui_dir,
    get_logs_dir,
    get_platform_env_dir,
    get_timestamp,
    get_venv_dir,
    get_venv_python,
    get_workspace_dir,
    is_windows,
    rel_path,
    rotate_logs,
    run_uv_lock,
)
from patch_manager import sync_dynamic_patches

ATTENTION_MODES: dict[str, str] = {
    "flash": "--use-flash-attention",
    "sage": "--use-sage-attention",
    "split": "--use-split-cross-attention",
    "quad": "--use-quad-cross-attention",
    "pytorch": "--use-pytorch-cross-attention",
    "none": "",
}
DEFAULT_ATTENTION = "sage"
# Full ECMA-48 CSI/OSC ANSI escape stripper
ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _stream_tee(pipe: TextIO, console: TextIO, log_fp: TextIO) -> None:
    """Forward merged subprocess stream to console while writing clean ANSI-stripped text to log."""
    try:
        for line in iter(pipe.readline, ""):
            console.write(line)
            console.flush()
            log_fp.write(ANSI_ESCAPE_RE.sub("", line))
            log_fp.flush()
    except (ValueError, OSError):
        pass


# ---------------------------------------------------------------------------
# CLI & Network Inspection
# ---------------------------------------------------------------------------
def parse_cli_args(args: list[str]) -> tuple[str, str, list[str]]:
    if not args:
        return DEFAULT_ATTENTION, ATTENTION_MODES[DEFAULT_ATTENTION], []

    first = args[0].lower()
    if first in ATTENTION_MODES:
        return first, ATTENTION_MODES[first], args[1:]

    if first.startswith("-"):
        return DEFAULT_ATTENTION, ATTENTION_MODES[DEFAULT_ATTENTION], args

    Log.error(f"Unknown attention mode: '{args[0]}'")
    Log.info(f"Valid modes: {', '.join(ATTENTION_MODES.keys())} (or pass flags directly)")
    sys.exit(1)


def extract_host_and_port(args: list[str], default_host: str = "127.0.0.1", default_port: int = 8188) -> tuple[str, int]:
    host = default_host
    port = default_port

    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                pass
        elif arg.startswith("--port="):
            try:
                port = int(arg.split("=", 1)[1])
            except ValueError:
                pass
        elif arg == "--listen":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                cand = args[i + 1]
                host = "127.0.0.1" if cand in ("0.0.0.0", "::") else cand
        elif arg.startswith("--listen="):
            cand = arg.split("=", 1)[1]
            host = "127.0.0.1" if cand in ("0.0.0.0", "::") else cand

    return host, port


def check_comfy_status(port: int, host: str = "127.0.0.1") -> tuple[bool, dict | None]:
    url = f"http://{host}:{port}/queue"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ComfyWrapper/2.0"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ConnectionRefusedError, OSError, ValueError):
        return False, None


def request_vram_unload(port: int, host: str = "127.0.0.1") -> None:
    url = f"http://{host}:{port}/free"
    payload = json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "ComfyWrapper/2.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=1.5):
            pass
    except Exception:
        pass


def get_pid_listening_on_port(port: int) -> int | None:
    port_suffix = f":{port}"
    if is_windows():
        try:
            out = subprocess.check_output(["netstat", "-ano", "-p", "tcp"], text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[3].upper() == "LISTENING" and parts[1].endswith(port_suffix):
                    return int(parts[4])
        except Exception:
            return None
    else:
        for cmd in (
            ["lsof", "-i", f"TCP:{port}", "-sTCP:LISTEN", "-t"],
            ["ss", "-lptn", f"sport = :{port}"],
        ):
            try:
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                if cmd[0] == "lsof":
                    if pids := out.strip().split():
                        return int(pids[0])
                elif m := re.search(r"pid=(\d+)", out):
                    return int(m.group(1))
            except Exception:
                continue
    return None


def terminate_process(pid: int, timeout_sec: float = 4.0) -> bool:
    if is_windows():
        try:
            return subprocess.run(["taskkill", "/F", "/PID", str(pid), "/T"], capture_output=True).returncode == 0
        except Exception:
            return False

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except Exception as e:
        Log.warn(f"Failed to send SIGTERM to PID {pid}: {e}")
        return False

    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
            time.sleep(0.15)
        except ProcessLookupError:
            return True

    try:
        os.kill(pid, signal.SIGKILL)
        return True
    except ProcessLookupError:
        return True
    except Exception:
        return False


def wait_for_port_free(port: int, host: str = "127.0.0.1", timeout_sec: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.15)
            if s.connect_ex((host, port)) != 0 and get_pid_listening_on_port(port) is None:
                return True
        time.sleep(0.15)
    return False


def _stop_instance(pid: int | None, port: int, host: str, flush_vram: bool = True) -> None:
    if flush_vram:
        request_vram_unload(port, host)
    if pid:
        terminate_process(pid)
    wait_for_port_free(port, host)


def handle_existing_instance(port: int, host: str = "127.0.0.1") -> None:
    is_comfy, queue_data = check_comfy_status(port, host)
    pid = get_pid_listening_on_port(port)

    if not is_comfy and pid is None:
        return

    if is_comfy and queue_data is not None:
        running = queue_data.get("queue_running", [])
        pending = queue_data.get("queue_pending", [])

        if not running and not pending:
            Log.info(f"Detected idle ComfyUI instance on port {port} (PID: {pid or 'unknown'}).")
            Log.info("Flushing VRAM & terminating idle instance...")
            _stop_instance(pid, port, host, flush_vram=True)
            Log.ok(f"Idle instance terminated. Port {port} is ready.\n")
            return

        Log.warn(f"Existing ComfyUI instance on port {port} (PID: {pid or 'unknown'}) is BUSY!")
        Log.warn(f"Running tasks: {len(running)} | Pending in queue: {len(pending)}")
        if confirm_action("Force terminate busy ComfyUI instance?"):
            Log.info(f"Force terminating busy instance (PID: {pid or 'unknown'})...")
            _stop_instance(pid, port, host, flush_vram=True)
            Log.ok(f"Busy instance terminated. Port {port} is ready.\n")
            return

        Log.info("Launch aborted. Existing ComfyUI instance was kept running.")
        sys.exit(0)

    if pid is not None:
        Log.warn(f"Port {port} is occupied by a non-ComfyUI or unresponsive process (PID: {pid}).")
        if confirm_action(f"Terminate process {pid} on port {port}?"):
            _stop_instance(pid, port, host, flush_vram=False)
            Log.ok(f"Process {pid} terminated. Port {port} is ready.\n")
        else:
            Log.info("Launch aborted.")
            sys.exit(0)


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------
def run_comfy(args: list[str]) -> None:
    workspace_dir = get_workspace_dir()
    comfyui_dir = get_comfyui_dir()
    platform_env_dir = get_platform_env_dir()
    logs_dir = get_logs_dir()

    if (rotated := rotate_logs(max_days=30)) > 0:
        Log.clean(f"Cleaned {rotated} expired log file(s) (>30 days)")

    sync_dynamic_patches()

    main_py = comfyui_dir / "main.py"
    if not main_py.exists():
        Log.error(f"ComfyUI entry point not found: {main_py}")
        sys.exit(1)

    attn_mode, attn_flag, extra_args = parse_cli_args(args)
    host, port = extract_host_and_port(extra_args, default_port=8188)
    handle_existing_instance(port, host)

    venv_path = get_venv_dir()
    python_exe = get_venv_python(venv_path)

    cmd = [str(python_exe), str(main_py)]
    if attn_flag:
        cmd.append(attn_flag)
    cmd.extend(extra_args)

    if not any(arg == "--verbose" or arg.startswith("--verbose=") for arg in extra_args):
        cmd.extend(["--verbose", "INFO"])

    env = get_clean_uv_env(venv_path)
    env["PYTHONUNBUFFERED"] = "1"
    if os.environ.get("NO_COLOR") is None:
        env.setdefault("FORCE_COLOR", "1")

    pythonpath = str(comfyui_dir)
    if env.get("PYTHONPATH"):
        pythonpath = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONPATH"] = pythonpath

    log_file = logs_dir / f"comfyui_{get_timestamp()}.log"

    Log.info("Starting ComfyUI...")
    print(f"    Attention : {attn_mode}" + (f" ({attn_flag})" if attn_flag else ""))
    print(f"    Endpoint  : http://{host}:{port}")
    print(f"    Venv      : {venv_path}")
    print(f"    SessionLog: {rel_path(log_file)}\n")

    exit_code = 0
    proc: subprocess.Popen | None = None
    with open(log_file, "w", encoding="utf-8", errors="replace") as log_fp:
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=workspace_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert proc.stdout is not None
            t_out = threading.Thread(target=_stream_tee, args=(proc.stdout, sys.stdout, log_fp), daemon=True)
            t_out.start()

            exit_code = proc.wait()
            t_out.join(timeout=1.5)
        except KeyboardInterrupt:
            print()
            Log.info("Interrupt received (Ctrl+C). Waiting for ComfyUI to shut down cleanly...")
            if proc and proc.poll() is None:
                try:
                    proc.wait(timeout=8.0)
                except subprocess.TimeoutExpired:
                    Log.warn("ComfyUI did not exit in time, forcing termination...")
                    proc.kill()
            exit_code = 0

    print()
    run_uv_lock(platform_env_dir, venv_dir=venv_path, skip_if_fresh=True, timeout=20.0)
    sys.exit(exit_code)


if __name__ == "__main__":
    run_comfy(sys.argv[1:])