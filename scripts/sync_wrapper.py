#!/usr/bin/env python3
"""Sync wrapper pyproject.toml with upstream ComfyUI changes and wrapper_config.toml.

Generates platform-specific environments in envs/windows/ and envs/linux/.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

from common import (
    Log,
    get_comfyui_dir,
    get_workspace_dir,
    is_windows,
    read_clean_lines,
    rel_path,
    run_uv_lock,
    run_uv_sync,
)
from patch_manager import sync_dynamic_patches


def generate_platform_pyproject(
    platform_name: str,
    output_dir: Path,
    base_pyproject_text: str,
    core_deps: list[str],
    wrapper_config: dict,
) -> None:
    """Generate platform-specific pyproject.toml atomically."""
    Log.info(f"Generating pyproject.toml for {platform_name}...")

    text = base_pyproject_text
    custom_deps: list[str] = wrapper_config.get("dependencies", {}).get("custom", [])

    valid_custom_deps: list[str] = []
    for dep in custom_deps:
        if dep.startswith("git+") and "@" not in dep:
            Log.note(f"   Skipping bare git URL (handled by Manager): {dep}")
            continue
        valid_custom_deps.append(dep)

    platform_key = platform_name.lower()
    platform_deps: dict[str, str] = {
        k: v
        for k, v in wrapper_config.get("dependencies", {}).get(platform_key, {}).items()
        if k != "python"
    }

    platform_lines: list[str] = []
    for pkg_name, pkg_spec in platform_deps.items():
        if pkg_spec.startswith(("http://", "https://", "git+", "file://")):
            platform_lines.append(f'    "{pkg_name} @ {pkg_spec}",')
        else:
            platform_lines.append(f'    "{pkg_name}{pkg_spec}",')

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
            f"    # Platform-specific dependencies ({platform_name})",
            *platform_lines,
        ])

    deps_lines.append("]")
    deps_block = "\n".join(deps_lines) + "\n"

    # Strip any upstream [tool.uv*] sections to prevent duplicate TOML table collisions
    text = re.sub(r"(?ms)^\[tool\.uv.*?\Z", "", text)

    project_pattern = re.compile(r"(?ms)^\[project\]\n(.*?)(?=^\[|\Z)")
    match = project_pattern.search(text)
    if not match:
        Log.error("[project] section not found in ComfyUI/pyproject.toml")
        sys.exit(1)

    project_section = re.sub(r"(?ms)^\s*dependencies\s*=\s*\[.*?^\]\s*\n", "", match.group(1))

    lines = project_section.splitlines(keepends=True)
    updated_lines: list[str] = []
    inserted = False

    platform_python = wrapper_config.get("dependencies", {}).get(platform_key, {}).get("python")

    for line in lines:
        if re.match(r"^\s*requires-python\s*=", line):
            if platform_python:
                line = f'requires-python = "{platform_python}"\n'
            updated_lines.append(line)
            if not inserted:
                if not line.endswith("\n"):
                    updated_lines.append("\n")
                updated_lines.append(deps_block)
                inserted = True
        else:
            updated_lines.append(line)

    if not inserted:
        if updated_lines and not updated_lines[-1].endswith("\n"):
            updated_lines.append("\n")
        updated_lines.append("\n" + deps_block)

    new_project_section = "".join(updated_lines)
    text = text[: match.start(1)] + new_project_section + text[match.end(1) :]

    pytorch_cfg = wrapper_config["pytorch"]
    pytorch_index_name: str = pytorch_cfg["index_name"]
    pytorch_index_url: str = pytorch_cfg["index_url"]
    torchaudio_index_name: str = pytorch_cfg.get("torchaudio_index_name", pytorch_index_name)
    torchaudio_index_url: str = pytorch_cfg.get("torchaudio_index_url", pytorch_index_url)

    platform_sys = "linux" if platform_key == "linux" else "win32"

    indices_block = f"""
[[tool.uv.index]]
name = "{pytorch_index_name}"
url = "{pytorch_index_url}"
explicit = true
"""
    if torchaudio_index_name != pytorch_index_name:
        indices_block += f"""
[[tool.uv.index]]
name = "{torchaudio_index_name}"
url = "{torchaudio_index_url}"
explicit = true
"""

    uv_block = f"""{indices_block}
[tool.uv.sources]
torch = {{ index = "{pytorch_index_name}" }}
torchvision = {{ index = "{pytorch_index_name}" }}
torchaudio = {{ index = "{torchaudio_index_name}" }}

[tool.uv]
find-links = ["../../wheels"]
environments = ["sys_platform == '{platform_sys}'"]
override-dependencies = []
"""

    extra_build_cfg = wrapper_config.get("uv", {}).get("extra_build_deps", {})
    common_build_deps: dict = {k: v for k, v in extra_build_cfg.items() if isinstance(v, list)}
    platform_build_deps: dict = extra_build_cfg.get(platform_key, {})
    all_build_deps = {**common_build_deps, **platform_build_deps}

    if all_build_deps:
        uv_block += "\n[tool.uv.extra-build-dependencies]\n"
        for pkg, deps in all_build_deps.items():
            deps_str = "[" + ", ".join(f'"{d}"' for d in deps) + "]"
            uv_block += f"{pkg} = {deps_str}\n"

    final_text = text.rstrip() + "\n\n" + uv_block.lstrip()

    output_pyproject = output_dir / "pyproject.toml"
    # Only write if content changed to preserve file mtime for smart lock skipping
    if not output_pyproject.exists() or output_pyproject.read_text(encoding="utf-8") != final_text:
        output_pyproject.write_text(final_text, encoding="utf-8")
        Log.ok(f"   Updated {rel_path(output_pyproject)}")
    else:
        Log.ok(f"   Unchanged {rel_path(output_pyproject)}")


def sync_platform_env(platform_name: str, platform_dir: Path) -> bool:
    """Sync platform-specific environment (uv lock + sync) using consolidated runners."""
    Log.info(f"Syncing {platform_name} environment...")
    return run_uv_lock(platform_dir) and run_uv_sync(platform_dir)


def sync_wrapper(sync_patches: bool = True) -> None:
    """Sync wrapper pyproject.toml for all platforms."""
    workspace_dir = get_workspace_dir()
    comfyui_dir = get_comfyui_dir()

    comfyui_pyproject = comfyui_dir / "pyproject.toml"
    comfyui_requirements = comfyui_dir / "requirements.txt"
    wrapper_config_path = workspace_dir / "wrapper_config.toml"

    for required_path in (comfyui_pyproject, comfyui_requirements, wrapper_config_path):
        if not required_path.exists():
            Log.error(f"Required file not found: {required_path}")
            sys.exit(1)

    Log.info("Syncing wrapper with ComfyUI/pyproject.toml + requirements.txt...")

    base_pyproject_text = comfyui_pyproject.read_text(encoding="utf-8")
    core_deps = read_clean_lines(comfyui_requirements, ignore_prefixes=("-",))
    with wrapper_config_path.open("rb") as f:
        wrapper_config = tomllib.load(f)

    envs_dir = workspace_dir / "envs"
    platforms = {
        "Windows": envs_dir / "windows",
        "Linux": envs_dir / "linux",
    }

    for plat_name, plat_dir in platforms.items():
        plat_dir.mkdir(parents=True, exist_ok=True)
        generate_platform_pyproject(plat_name, plat_dir, base_pyproject_text, core_deps, wrapper_config)

    active_plat, other_plat = ("Windows", "Linux") if is_windows() else ("Linux", "Windows")
    if not sync_platform_env(active_plat, platforms[active_plat]):
        sys.exit(1)
    Log.note(f"{other_plat} pyproject.toml generated (run on {other_plat} to sync {other_plat} venv).")

    if sync_patches:
        sync_dynamic_patches()

    Log.ok("Sync complete!")


if __name__ == "__main__":
    sync_wrapper()