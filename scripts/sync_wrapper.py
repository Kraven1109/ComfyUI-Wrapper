#!/usr/bin/env python3
"""Sync wrapper pyproject.toml with upstream ComfyUI changes and wrapper_config.toml."""

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


def sync_wrapper() -> None:
    """Sync wrapper pyproject.toml from upstream + config."""
    workspace_dir = get_workspace_dir()
    comfyui_dir = get_comfyui_dir()
    
    comfyui_pyproject = comfyui_dir / "pyproject.toml"
    comfyui_requirements = comfyui_dir / "requirements.txt"
    wrapper_config = workspace_dir / "wrapper_config.toml"
    wrapper_pyproject = workspace_dir / "pyproject.toml"
    
    if not comfyui_pyproject.exists():
        print(f"Error: {comfyui_pyproject} not found", file=sys.stderr)
        sys.exit(1)
    
    if not comfyui_requirements.exists():
        print(f"Error: {comfyui_requirements} not found", file=sys.stderr)
        sys.exit(1)
    
    if not wrapper_config.exists():
        print(f"Error: {wrapper_config} not found", file=sys.stderr)
        sys.exit(1)
    
    print("🔄 Syncing wrapper with ComfyUI/pyproject.toml + requirements.txt...")
    
    # Load wrapper config
    with wrapper_config.open("rb") as f:
        config = tomllib.load(f)
    
    custom_deps: list[str] = config["dependencies"]["custom"]
    pytorch_index_name: str = config["pytorch"]["index_name"]
    pytorch_index_url: str = config["pytorch"]["index_url"]
    
    # Read upstream pyproject.toml
    text = comfyui_pyproject.read_text(encoding="utf-8")
    
    # Read core dependencies from requirements.txt
    core_deps = read_requirements(comfyui_requirements)
    
    # Filter out invalid git URLs from custom_deps
    # Git URLs need package name: "package_name @ git+https://..."
    valid_custom_deps = []
    for dep in custom_deps:
        # Skip bare git+ URLs (ComfyUI-Manager will handle them)
        if dep.startswith("git+") and "@" not in dep:
            print(f"⚠ Skipping bare git URL (Manager will handle): {dep}")
            continue
        valid_custom_deps.append(dep)
    
    # Build dependencies block
    deps_lines = [
        "dependencies = [",
        "    # Core ComfyUI dependencies (auto-synced from ComfyUI/requirements.txt)",
        *[f'    "{dep}",' for dep in core_deps],
        "",
        "    # Additional custom node dependencies (from wrapper_config.toml)",
        *[f'    "{dep}",' for dep in valid_custom_deps],
        "]",
    ]
    
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
# Exclude problematic packages that ComfyUI doesn't actually need
override-dependencies = [
    # flash-attn is very hard to build and ComfyUI works fine without it
]
"""
    
    text = text.rstrip() + "\n\n" + uv_block.lstrip()
    wrapper_pyproject.write_text(text, encoding="utf-8")
    
    print("✓ Wrapper synced! Updating lockfile...")
    
    # Run uv lock
    result = subprocess.run(["uv", "lock"], cwd=workspace_dir, check=False)
    if result.returncode != 0:
        print("Warning: uv lock failed", file=sys.stderr)
        sys.exit(1)
    
    print("✓ Lock updated! Syncing environment...")
    
    # Run uv sync
    result = subprocess.run(["uv", "sync"], cwd=workspace_dir, check=False)
    if result.returncode != 0:
        print("Warning: uv sync failed", file=sys.stderr)
        sys.exit(1)
    
    print()
    print("✓ Sync complete! Environment is ready.")


if __name__ == "__main__":
    sync_wrapper()
