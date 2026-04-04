#!/usr/bin/env python3
"""Sync wrapper pyproject.toml with upstream ComfyUI changes and wrapper_config.toml.

Generates platform-specific environments in envs/windows/ and envs/linux/.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

from common import get_comfyui_dir, get_workspace_dir


def read_requirements(path: Path) -> list[str]:
    """Read requirements.txt and return list of dependencies."""
    items: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        items.append(stripped)
    return items


def generate_platform_pyproject(
    platform: str,
    output_dir: Path,
    comfyui_pyproject: Path,
    comfyui_requirements: Path,
    wrapper_config: dict,
) -> None:
    """Generate platform-specific pyproject.toml."""
    print(f"\n[*] Generating pyproject.toml for {platform}...")
    
    # Read upstream pyproject.toml
    text = comfyui_pyproject.read_text(encoding="utf-8")
    
    # Read core dependencies from requirements.txt
    core_deps = read_requirements(comfyui_requirements)
    
    # Get custom dependencies
    custom_deps: list[str] = wrapper_config["dependencies"]["custom"]
    
    # Filter out invalid git URLs from custom_deps
    valid_custom_deps = []
    for dep in custom_deps:
        # Skip bare git+ URLs (ComfyUI-Manager will handle them)
        if dep.startswith("git+") and "@" not in dep:
            print(f"   [SKIP] Bare git URL (Manager will handle): {dep}")
            continue
        valid_custom_deps.append(dep)
    
    # Get platform-specific dependencies
    platform_deps: dict[str, str] = {}
    if platform == "Windows":
        platform_deps = wrapper_config.get("dependencies", {}).get("windows", {})
    else:  # Linux or macOS
        platform_deps = wrapper_config.get("dependencies", {}).get("linux", {})
    
    # Filter out 'python' key (already handled by requires-python in [project])
    platform_deps = {k: v for k, v in platform_deps.items() if k != "python"}
    
    # Build platform-specific lines WITHOUT environment markers
    # (each pyproject.toml is platform-specific already)
    platform_lines = []
    for pkg_name, pkg_spec in platform_deps.items():
        if pkg_spec.startswith("http") or pkg_spec.startswith("git+"):
            # URL-based dependency
            platform_lines.append(f'    "{pkg_name} @ {pkg_spec}",')
        elif pkg_spec.startswith("file://"):
            # Local file URL
            platform_lines.append(f'    "{pkg_name} @ {pkg_spec}",')
        else:
            # Version specifier
            platform_lines.append(f'    "{pkg_name}{pkg_spec}",')
    
    # Build dependencies block
    deps_lines = [
        "dependencies = [",
        "    # Core ComfyUI dependencies (auto-synced from ComfyUI/requirements.txt)",
        *[f'    "{dep}",' for dep in core_deps],
        "",
        "    # Additional custom node dependencies (from wrapper_config.toml)",
        *[f'    "{dep}",' for dep in valid_custom_deps],
    ]
    
    if platform_lines:
        deps_lines.extend([
            "",
            f"    # Platform-specific dependencies ({platform})",
            *platform_lines,
        ])
    
    deps_lines.append("]")
    deps_block = "\n".join(deps_lines) + "\n"
    
    # Find [project] section
    project_pattern = re.compile(r"(?ms)^\[project\]\n(.*?)(?=^\[|\Z)")
    match = project_pattern.search(text)
    if not match:
        print("Error: [project] section not found in ComfyUI/pyproject.toml", file=sys.stderr)
        sys.exit(1)
    
    project_section = match.group(1)
    
    # Remove any existing dependencies block
    project_section = re.sub(r"(?ms)^\s*dependencies\s*=\s*\[.*?^\]\s*\n", "", project_section)
    
    # Insert dependencies after requires-python
    lines = project_section.splitlines(keepends=True)
    updated_lines: list[str] = []
    inserted = False
    
    for line in lines:
        updated_lines.append(line)
        if not inserted and re.match(r"^\s*requires-python\s*=", line):
            if not line.endswith("\n"):
                updated_lines.append("\n")
            updated_lines.append(deps_block)
            inserted = True
    
    if not inserted:
        if updated_lines and not updated_lines[-1].endswith("\n"):
            updated_lines.append("\n")
        updated_lines.append("\n" + deps_block)
    
    new_project_section = "".join(updated_lines)
    text = text[:match.start(1)] + new_project_section + text[match.end(1):]
    
    # Add uv overrides at the end
    pytorch_index_name: str = wrapper_config["pytorch"]["index_name"]
    pytorch_index_url: str = wrapper_config["pytorch"]["index_url"]
    
    platform_sys = "linux" if platform.lower() == "linux" else "win32"
    
    uv_block = f"""
[[tool.uv.index]]
name = "{pytorch_index_name}"
url = "{pytorch_index_url}"
explicit = true

[tool.uv.sources]
# Override PyTorch index (from wrapper_config.toml)
torch = {{ index = "{pytorch_index_name}" }}
torchvision = {{ index = "{pytorch_index_name}" }}
torchaudio = {{ index = "{pytorch_index_name}" }}

[tool.uv]
# Platform-specific lock for {platform} only — prevents cross-platform resolution failures
environments = ["sys_platform == '{platform_sys}'"]

# Exclude problematic packages that ComfyUI doesn't actually need
override-dependencies = [
    # flash-attn is very hard to build and ComfyUI works fine without it
]
"""
    
    # Add extra-build-dependencies from wrapper_config.toml [uv.extra_build_deps]
    extra_build_cfg = wrapper_config.get("uv", {}).get("extra_build_deps", {})
    # Top-level list values = common to all platforms; sub-table keys = platform-specific
    common_build_deps: dict = {k: v for k, v in extra_build_cfg.items() if isinstance(v, list)}
    platform_build_deps: dict = extra_build_cfg.get(platform.lower(), {})
    all_build_deps = {**common_build_deps, **platform_build_deps}

    if all_build_deps:
        uv_block += """
[tool.uv.extra-build-dependencies]
# Extra build dependencies for packages that need them at build time
"""
        for pkg, deps in all_build_deps.items():
            deps_str = "[" + ", ".join(f'"{d}"' for d in deps) + "]"
            uv_block += f"{pkg} = {deps_str}\n"
    
    text = text.rstrip() + "\n\n" + uv_block.lstrip()
    
    # Write to platform-specific directory
    output_pyproject = output_dir / "pyproject.toml"
    output_pyproject.write_text(text, encoding="utf-8")
    print(f"   [OK] Generated {output_pyproject.relative_to(get_workspace_dir())}")


def sync_platform_env(platform: str, platform_dir: Path) -> None:
    """Sync platform-specific environment (uv lock + sync)."""
    print(f"\n[*] Syncing {platform} environment...")
    
    # Run uv lock (with preview-features flag to suppress warning)
    lock_cmd = ["uv", "lock"]
    if platform.lower() in ("linux", "windows"):
        lock_cmd.extend(["--preview-features", "extra-build-dependencies"])
    
    result = subprocess.run(
        lock_cmd,
        cwd=platform_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"   [ERROR] uv lock failed for {platform}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return
    
    print(f"   [OK] Lock file updated: {platform_dir.relative_to(get_workspace_dir())}/uv.lock")
    
    # Run uv sync
    sync_cmd = ["uv", "sync"]
    if platform.lower() == "linux":
        sync_cmd.extend(["--python-platform", "linux", "--preview-features", "extra-build-dependencies"])
    elif platform.lower() == "windows":
        sync_cmd.extend(["--preview-features", "extra-build-dependencies"])
    
    result = subprocess.run(
        sync_cmd,
        cwd=platform_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"   [ERROR] uv sync failed for {platform}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return
    
    import os as _os
    actual_venv = _os.environ.get("UV_PROJECT_ENVIRONMENT") or str(platform_dir / ".venv")
    print(f"   [OK] Environment synced: {actual_venv}")


def sync_wrapper() -> None:
    """Sync wrapper pyproject.toml for all platforms."""
    workspace_dir = get_workspace_dir()
    comfyui_dir = get_comfyui_dir()
    
    comfyui_pyproject = comfyui_dir / "pyproject.toml"
    comfyui_requirements = comfyui_dir / "requirements.txt"
    wrapper_config_path = workspace_dir / "wrapper_config.toml"
    
    # Validate paths
    if not comfyui_pyproject.exists():
        print(f"Error: {comfyui_pyproject} not found", file=sys.stderr)
        sys.exit(1)
    
    if not comfyui_requirements.exists():
        print(f"Error: {comfyui_requirements} not found", file=sys.stderr)
        sys.exit(1)
    
    if not wrapper_config_path.exists():
        print(f"Error: {wrapper_config_path} not found", file=sys.stderr)
        sys.exit(1)
    
    print("[*] Syncing wrapper with ComfyUI/pyproject.toml + requirements.txt...")
    
    # Load wrapper config
    with wrapper_config_path.open("rb") as f:
        wrapper_config = tomllib.load(f)
    
    # Create envs directories if they don't exist
    envs_dir = workspace_dir / "envs"
    windows_dir = envs_dir / "windows"
    linux_dir = envs_dir / "linux"
    
    windows_dir.mkdir(parents=True, exist_ok=True)
    linux_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate pyproject.toml for both platforms
    generate_platform_pyproject(
        "Windows",
        windows_dir,
        comfyui_pyproject,
        comfyui_requirements,
        wrapper_config,
    )
    
    generate_platform_pyproject(
        "Linux",
        linux_dir,
        comfyui_pyproject,
        comfyui_requirements,
        wrapper_config,
    )
    
    # Sync environments (on current platform only)
    import platform
    current_platform = platform.system()
    
    if current_platform == "Windows":
        sync_platform_env("Windows", windows_dir)
        print("\n[NOTE] Linux environment files generated but NOT synced (run on Linux to sync)")
    elif current_platform in ("Linux", "Darwin"):
        sync_platform_env("Linux", linux_dir)
        print("\n[NOTE] Windows environment files generated but NOT synced (run on Windows to sync)")
    
    print("\n[OK] Sync complete!")
    print("\nStructure:")
    print(f"   envs/windows/  -> Windows-specific venv + pyproject.toml + uv.lock")
    print(f"   envs/linux/    -> Linux-specific venv + pyproject.toml + uv.lock")
    print(f"   wrapper_config.toml -> Shared configuration")
    print(f"\nNext steps:")
    print(f"   * Windows users: comfy.bat will use envs/windows/")
    print(f"   * Linux users: comfy.sh will use envs/linux/")


if __name__ == "__main__":
    sync_wrapper()
