#!/usr/bin/env python3
"""Dynamic Patch Manager for ComfyUI Portable Workspace."""

from __future__ import annotations

import enum
import os
import subprocess
import sys
from pathlib import Path

from common import (
    Log,
    get_comfyui_dir,
    get_workspace_dir,
    has_git,
    is_windows,
    read_clean_lines,
    rel_path,
    run_git,
)


class PatchStatus(enum.Enum):
    """Status of a Category B git patch."""

    APPLIED = "APPLIED"
    CAN_APPLY = "CAN_APPLY"
    CONFLICT = "CONFLICT"


def get_patches_dir() -> Path:
    return get_workspace_dir() / "patches"


def load_patch_manifest() -> list[str] | None:
    manifest_file = get_patches_dir() / "patches.txt"
    if not manifest_file.is_file():
        return None
    return [line.replace("\\", "/").rstrip("/") for line in read_clean_lines(manifest_file)]


def _is_category_a_dir(path: Path) -> bool:
    return path.is_dir() and (path / "__init__.py").exists()


def _is_link(path: Path) -> bool:
    """Detect symlink or Windows NTFS junction (even if target is broken)."""
    if path.is_symlink():
        return True
    if hasattr(path, "is_junction"):
        return path.is_junction()
    return False


def _git_root(path: Path) -> Path | None:
    if not has_git():
        return None
    try:
        res = run_git(["rev-parse", "--show-toplevel"], cwd=path)
        if res.returncode == 0:
            return Path(res.stdout.strip()).resolve()
    except Exception:
        pass
    return None


def _norm(path: Path) -> str:
    try:
        s = str(path.resolve())
    except OSError:
        s = str(path)
    return s.lower() if is_windows() else s


# ============================================================================
# Category A: Directory Links (Web Hooks & Runtime Extensions)
# ============================================================================
def _create_directory_link(source_dir: Path, target_link: Path) -> bool:
    source_str = str(source_dir.resolve())
    target_str = str(target_link)

    if target_link.exists() or _is_link(target_link):
        try:
            if target_link.exists() and _norm(target_link.resolve()) == _norm(source_dir):
                return True
            _remove_directory_link(target_link)
        except Exception:
            pass

    if is_windows():
        try:
            import _winapi  # type: ignore[import]

            _winapi.CreateJunction(source_str, target_str)
            return True
        except Exception:
            try:
                res = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", target_str, source_str],
                    capture_output=True,
                    text=True,
                )
                return res.returncode == 0
            except Exception as e:
                Log.error(f"Failed creating junction for {target_link.name}: {e}")
                return False
    else:
        try:
            os.symlink(source_str, target_str, target_is_directory=True)
            return True
        except Exception as e:
            Log.error(f"Failed creating symlink for {target_link.name}: {e}")
            return False


def _remove_directory_link(link_path: Path) -> None:
    try:
        if link_path.is_symlink():
            link_path.unlink()
        else:
            os.rmdir(str(link_path))
    except Exception:
        pass


def _protect_link_from_git(link_path: Path) -> None:
    try:
        gitignore = link_path.parent / ".gitignore"
        existing_lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
        if link_path.name not in existing_lines:
            gitignore.write_text("\n".join([*existing_lines, link_path.name]) + "\n", encoding="utf-8")
    except Exception:
        pass


def sync_dynamic_links() -> int:
    patches_dir = get_patches_dir()
    custom_nodes_dir = get_comfyui_dir() / "custom_nodes"

    if not custom_nodes_dir.exists():
        return 0

    manifest = load_patch_manifest()
    active_patch_names: set[str] = set()

    if patches_dir.exists():
        for item in sorted(patches_dir.iterdir()):
            if _is_category_a_dir(item):
                if manifest is not None and item.name not in manifest:
                    continue
                active_patch_names.add(item.name)
                target_link = custom_nodes_dir / item.name
                if _create_directory_link(item, target_link):
                    _protect_link_from_git(target_link)
                    Log.ok(f"Dynamic patch linked: patches/{item.name} -> custom_nodes/{item.name}")

    patches_dir_norm = _norm(patches_dir)
    for existing_node in custom_nodes_dir.iterdir():
        try:
            is_orphan_broken_link = _is_link(existing_node) and not existing_node.exists()
            points_to_patches = _norm(existing_node.resolve()).startswith(patches_dir_norm)
            if is_orphan_broken_link or (points_to_patches and existing_node.name not in active_patch_names):
                Log.clean(f"Removed orphan patch link: custom_nodes/{existing_node.name}")
                _remove_directory_link(existing_node)
        except Exception:
            pass

    return len(active_patch_names)


# ============================================================================
# Category B: Unified Diff Git Patches (*.patch / *.diff)
# ============================================================================
def find_patch_files() -> list[Path]:
    patches_dir = get_patches_dir()
    if not patches_dir.is_dir():
        return []

    manifest = load_patch_manifest()
    if manifest is not None:
        patch_files: list[Path] = []
        for entry in manifest:
            if not entry.endswith((".patch", ".diff")):
                continue
            patch_path = patches_dir / Path(entry)
            if patch_path.is_file():
                patch_files.append(patch_path)
            else:
                Log.warn(f"Manifest patch not found: patches/{entry}")
        return patch_files

    return sorted(
        p
        for ext in ("*.patch", "*.diff")
        for p in patches_dir.rglob(ext)
        if not _is_category_a_dir(patches_dir / p.relative_to(patches_dir).parts[0])
    )


def _resolve_patch_target_dir(patch_path: Path) -> Path:
    workspace_dir = get_workspace_dir()
    comfyui_dir = get_comfyui_dir()

    try:
        rel = patch_path.relative_to(get_patches_dir())
    except ValueError:
        return workspace_dir

    if len(rel.parts) > 1:
        target_name = rel.parts[0]
        candidate = comfyui_dir / "custom_nodes" / target_name
        if candidate.exists() and _git_root(candidate) is not None:
            return candidate
        if target_name.lower() == "comfyui" and comfyui_dir.exists():
            return comfyui_dir

    return workspace_dir


def check_git_patch(patch_path: Path, target_dir: Path | None = None) -> tuple[PatchStatus, Path]:
    if not has_git():
        raise RuntimeError("git is not available on PATH — cannot manage Category B patches.")

    target_dir = target_dir or _resolve_patch_target_dir(patch_path)
    patch_abs = str(patch_path.resolve())

    def _try(cwd: Path) -> PatchStatus | None:
        if run_git(["apply", "--reverse", "--check", "--ignore-whitespace", patch_abs], cwd=cwd).returncode == 0:
            return PatchStatus.APPLIED
        if run_git(["apply", "--check", "--ignore-whitespace", patch_abs], cwd=cwd).returncode == 0:
            return PatchStatus.CAN_APPLY
        return None

    for candidate in dict.fromkeys((target_dir, get_workspace_dir(), get_comfyui_dir())):
        if (status := _try(candidate)) is not None:
            return status, candidate

    return PatchStatus.CONFLICT, target_dir


def _execute_git_patch(patch_path: Path, reverse: bool = False, target_dir: Path | None = None) -> bool:
    """Consolidated engine for both applying and reverting Category B git patches."""
    action_gerund = "reverting" if reverse else "applying"
    if not has_git():
        Log.warn(f"git not found — skipping {action_gerund} patch.")
        return False

    try:
        status, resolved_dir = check_git_patch(patch_path, target_dir)
    except RuntimeError as e:
        Log.error(str(e))
        return False

    rel = rel_path(patch_path)

    # Idempotent fast-paths
    if not reverse and status == PatchStatus.APPLIED:
        Log.ok(f"Git patch already applied: {rel}")
        return True
    if reverse and status == PatchStatus.CAN_APPLY:
        Log.note(f"Patch not applied (nothing to revert): {rel}")
        return True

    expected_status = PatchStatus.APPLIED if reverse else PatchStatus.CAN_APPLY
    if status == expected_status:
        args = ["apply", "--ignore-whitespace"]
        if reverse:
            args.insert(1, "--reverse")
        args.append(str(patch_path.resolve()))

        res = run_git(args, cwd=resolved_dir)
        if res.returncode == 0:
            arrow = f"<- {resolved_dir.name}" if reverse else f"-> {resolved_dir.name}"
            verb = "Reverted" if reverse else "Applied"
            Log.ok(f"{verb} git patch: {rel} {arrow}")
            return True
        Log.error(f"Failed {action_gerund} {rel}: {res.stderr.strip()}")
        return False

    Log.warn(f"Cannot {'revert' if reverse else 'apply'} git patch (conflict): {rel}")
    return False


def apply_git_patch(patch_path: Path, target_dir: Path | None = None) -> bool:
    return _execute_git_patch(patch_path, reverse=False, target_dir=target_dir)


def revert_git_patch(patch_path: Path, target_dir: Path | None = None) -> bool:
    return _execute_git_patch(patch_path, reverse=True, target_dir=target_dir)


def apply_all_git_patches() -> tuple[int, list[Path]]:
    if not has_git():
        return 0, []
    success = 0
    conflicts: list[Path] = []
    for p in find_patch_files():
        if apply_git_patch(p):
            success += 1
        else:
            conflicts.append(p)
    return success, conflicts


def revert_all_git_patches() -> int:
    return sum(1 for p in find_patch_files() if revert_git_patch(p)) if has_git() else 0


def sync_dynamic_patches(report_conflicts: bool = False) -> tuple[int, list[Path]]:
    link_count = sync_dynamic_links()
    patch_count, conflicts = apply_all_git_patches()

    if report_conflicts and conflicts:
        Log.warn(f"{len(conflicts)} git patch(es) could not be applied after update:")
        for c in conflicts:
            Log.warn(f"   - {rel_path(c)}")
        Log.info("Run `comfy patch status` for details.")

    return link_count + patch_count, conflicts


def patch_status_summary() -> None:
    patches_dir = get_patches_dir()
    if not patches_dir.is_dir():
        Log.note("No patches/ directory found.")
        return

    comfyui_dir = get_comfyui_dir()

    cat_a_dirs = [d for d in patches_dir.iterdir() if _is_category_a_dir(d)]
    print("\n--- Dynamic Runtime Extensions (Category A: Symlink/Junction) ---")
    if not cat_a_dirs:
        print("  (None)")
    else:
        for p in sorted(cat_a_dirs):
            target = comfyui_dir / "custom_nodes" / p.name
            is_valid_link = _is_link(target) and target.exists() and _norm(target.resolve()) == _norm(p)
            status = "[ACTIVE  (Linked)]" if is_valid_link else "[INACTIVE (Unlinked)]"
            print(f"  {status}  patches/{p.name}")

    print("\n--- Unified Diff Git Patches (Category B: git apply) ---")
    if not has_git():
        Log.warn("  git not found on PATH.")
        return
    patch_files = find_patch_files()
    if not patch_files:
        print("  (None)")
    else:
        for p in patch_files:
            try:
                status, target_dir = check_git_patch(p)
                status_str = {
                    PatchStatus.APPLIED: "[APPLIED          ]",
                    PatchStatus.CAN_APPLY: "[UNAPPLIED (Ready)]",
                    PatchStatus.CONFLICT: "[CONFLICT         ]",
                }.get(status, f"[{status}]")
                target_label = target_dir.name
            except RuntimeError as e:
                status_str = "[ERROR]"
                target_label = str(e)
            print(f"  {status_str}  {rel_path(p)}  (target: {target_label})")


def handle_patch_cli(args: list[str]) -> None:
    """Consolidated CLI dispatcher for patch subcommands."""
    subaction = args[0].lower() if args else "sync"
    match subaction:
        case "status" | "st":
            patch_status_summary()
        case "revert" | "rev":
            revert_all_git_patches()
        case "sync" | "apply":
            sync_dynamic_patches()
        case _:
            Log.error(f"Unknown patch action: '{subaction}' (expected: sync, status, revert)")
            sys.exit(1)


if __name__ == "__main__":
    handle_patch_cli(sys.argv[1:])