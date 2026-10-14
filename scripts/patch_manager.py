#!/usr/bin/env python3
"""Dynamic Patch Manager for ComfyUI Portable Workspace.

Handles both:
1. Dynamic Runtime Extensions / Web Hooks (Category A):
   Directories inside `patches/<name>/` with `__init__.py` are automatically
   junctioned/symlinked into `ComfyUI/custom_nodes/<name>`. If removed from
   `patches/`, the link in `custom_nodes/` is cleaned up automatically.
2. Unified Diff Git Patches (Category B):
   `*.patch` / `*.diff` files inside `patches/<target>/` (without `__init__.py`)
   are verified and applied via `git apply` with full idempotency checks.
"""

from __future__ import annotations

import enum
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from common import get_comfyui_dir, get_workspace_dir


# ============================================================================
# Types
# ============================================================================

class PatchStatus(enum.Enum):
    """Status of a Category B git patch."""
    APPLIED = "APPLIED"
    CAN_APPLY = "CAN_APPLY"
    CONFLICT = "CONFLICT"


# ============================================================================
# Shared Helpers
# ============================================================================

def get_patches_dir() -> Path:
    """Return the root patches directory."""
    return get_workspace_dir() / "patches"


def get_manifest_path() -> Path:
    """Return path to master patch manifest file (patches.txt)."""
    return get_patches_dir() / "patches.txt"


def load_patch_manifest() -> list[str] | None:
    """Load list of enabled relative patch paths from patches/patches.txt.

    Returns None if manifest does not exist (falls back to auto-discovery).
    Lines starting with '#' or empty lines are ignored.
    All entries are normalized with forward slashes.
    """
    manifest_file = get_manifest_path()
    if not manifest_file.exists() or not manifest_file.is_file():
        return None

    entries: list[str] = []
    for line in manifest_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        normalized = line.replace("\\", "/").rstrip("/")
        entries.append(normalized)
    return entries


def _has_git() -> bool:
    """Return True if git is available on PATH."""
    return shutil.which("git") is not None


def _is_category_a_dir(path: Path) -> bool:
    """Return True if `path` is a Category A patch directory (has __init__.py)."""
    return path.is_dir() and (path / "__init__.py").exists()


def _git_root(path: Path) -> Path | None:
    """Find the nearest .git root at or above `path`. Returns None if not a git repo."""
    if not _has_git():
        return None
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return Path(res.stdout.strip()).resolve()
    except Exception:
        pass
    return None


def _norm(path: Path) -> str:
    """Return a normalised (lowercase on Windows) string for path comparison."""
    try:
        s = str(path.resolve())
    except OSError:
        s = str(path)
    return s.lower() if platform.system() == "Windows" else s


# ============================================================================
# Category A: Directory Links (Web Hooks & Runtime Extensions)
# ============================================================================

def _create_directory_link(source_dir: Path, target_link: Path) -> bool:
    """Create a directory symlink or NTFS junction without requiring admin rights."""
    source_str = str(source_dir.resolve())
    target_str = str(target_link)

    # If target already exists, verify it points to the correct source
    if target_link.exists() or target_link.is_symlink():
        try:
            if _norm(target_link.resolve()) == _norm(source_dir):
                return True
            # Stale link — remove it
            _remove_directory_link(target_link)
        except Exception:
            pass

    # Create link
    if platform.system() == "Windows":
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
                print(
                    f"   [ERROR] Failed creating junction for {target_link.name}: {e}",
                    file=sys.stderr,
                )
                return False
    else:
        try:
            os.symlink(source_str, target_str, target_is_directory=True)
            return True
        except Exception as e:
            print(
                f"   [ERROR] Failed creating symlink for {target_link.name}: {e}",
                file=sys.stderr,
            )
            return False


def _remove_directory_link(link_path: Path) -> None:
    """Safely remove a symlink or NTFS junction without touching the target.

    IMPORTANT: Do NOT call .resolve() on junctions/symlinks here — .resolve()
    follows the link and returns the *target* path, not the link itself.
    We must operate on the link path directly.
    """
    try:
        if link_path.is_symlink():
            link_path.unlink()
        elif platform.system() == "Windows":
            # os.rmdir on a junction removes the junction pointer without
            # touching the target directory contents.
            os.rmdir(str(link_path))
        else:
            os.rmdir(str(link_path))
    except Exception:
        pass


def sync_dynamic_links() -> int:
    """Sync Category A patch directories from patches/ into ComfyUI/custom_nodes/."""
    patches_dir = get_patches_dir()
    comfyui_dir = get_comfyui_dir()
    custom_nodes_dir = comfyui_dir / "custom_nodes"

    if not custom_nodes_dir.exists():
        return 0

    manifest = load_patch_manifest()
    active_patch_names: set[str] = set()

    if patches_dir.exists():
        for item in patches_dir.iterdir():
            if _is_category_a_dir(item):
                # If manifest is present, item must be explicitly listed
                if manifest is not None and item.name not in manifest:
                    continue
                active_patch_names.add(item.name)
                target_link = custom_nodes_dir / item.name
                if _create_directory_link(item, target_link):
                    _protect_link_from_git(target_link)
                    print(
                        f"   [OK] Dynamic patch linked: patches/{item.name}"
                        f" -> custom_nodes/{item.name}"
                    )

    # Remove orphaned links that used to point into patches/
    patches_dir_norm = _norm(patches_dir)
    for existing_node in custom_nodes_dir.iterdir():
        try:
            resolved_norm = _norm(existing_node.resolve())
            if resolved_norm.startswith(patches_dir_norm):
                if existing_node.name not in active_patch_names:
                    print(
                        f"   [CLEAN] Removed orphan patch link: custom_nodes/{existing_node.name}"
                    )
                    _remove_directory_link(existing_node)
        except Exception:
            pass

    return len(active_patch_names)


def _protect_link_from_git(link_path: Path) -> None:
    """Append the link name to ComfyUI/custom_nodes/.gitignore if not already present."""
    try:
        gitignore = link_path.parent / ".gitignore"
        entry = link_path.name + "\n"
        if gitignore.exists():
            existing = gitignore.read_text(encoding="utf-8")
            if link_path.name in existing:
                return
            gitignore.write_text(existing.rstrip("\n") + "\n" + entry, encoding="utf-8")
        else:
            gitignore.write_text(entry, encoding="utf-8")
    except Exception:
        pass


# ============================================================================
# Category B: Unified Diff Git Patches (*.patch / *.diff)
# ============================================================================

def find_patch_files() -> list[Path]:
    """Find all *.patch / *.diff files in patches/ directories that are NOT Category A.

    If patches/patches.txt exists, returns only the listed files that end in .patch or .diff.
    Otherwise, discovers all *.patch and *.diff files recursively.
    """
    patches_dir = get_patches_dir()
    if not patches_dir.exists() or not patches_dir.is_dir():
        return []

    manifest = load_patch_manifest()
    if manifest is not None:
        patch_files: list[Path] = []
        for entry in manifest:
            if not (entry.endswith(".patch") or entry.endswith(".diff")):
                continue  # Category A directory entry
            patch_path = patches_dir / Path(entry)
            if patch_path.exists() and patch_path.is_file():
                patch_files.append(patch_path)
            else:
                print(f"   [WARN] Manifest patch not found: patches/{entry}", file=sys.stderr)
        return patch_files

    patch_files = []
    for ext in ("*.patch", "*.diff"):
        for p in patches_dir.rglob(ext):
            # Skip any file inside a Category A directory
            try:
                rel = p.relative_to(patches_dir)
            except ValueError:
                continue
            top_level = patches_dir / rel.parts[0]
            if _is_category_a_dir(top_level):
                continue
            patch_files.append(p)

    return sorted(patch_files)


def _resolve_patch_target_dir(patch_path: Path) -> Path:
    """Resolve the git working directory for a patch file.

    Resolution order:
    1. `ComfyUI/custom_nodes/<dirname>` if it is a git repo
    2. `ComfyUI/` if dirname matches "comfyui" (case-insensitive)
    3. Workspace root as last resort
    """
    workspace_dir = get_workspace_dir()
    comfyui_dir = get_comfyui_dir()

    try:
        rel = patch_path.relative_to(get_patches_dir())
    except ValueError:
        return workspace_dir

    if len(rel.parts) > 1:
        target_name = rel.parts[0]

        # Priority 1: ComfyUI/custom_nodes/<target>
        candidate = comfyui_dir / "custom_nodes" / target_name
        if candidate.exists() and _git_root(candidate) is not None:
            return candidate

        # Priority 2: explicit "ComfyUI" target
        if target_name.lower() == "comfyui" and comfyui_dir.exists():
            return comfyui_dir

    return workspace_dir


def check_git_patch(
    patch_path: Path,
    target_dir: Path | None = None,
) -> tuple[PatchStatus, Path]:
    """Return the status of a git patch and the directory it should be applied in."""
    if not _has_git():
        raise RuntimeError("git is not available on PATH — cannot manage Category B patches.")

    if target_dir is None:
        target_dir = _resolve_patch_target_dir(patch_path)

    patch_abs = str(patch_path.resolve())

    def _try(cwd: Path) -> PatchStatus | None:
        """Try reverse (applied?) then forward (applicable?) checks in `cwd`."""
        rev = subprocess.run(
            ["git", "apply", "--reverse", "--check", "--ignore-whitespace", patch_abs],
            cwd=cwd, capture_output=True, text=True,
        )
        if rev.returncode == 0:
            return PatchStatus.APPLIED
        fwd = subprocess.run(
            ["git", "apply", "--check", "--ignore-whitespace", patch_abs],
            cwd=cwd, capture_output=True, text=True,
        )
        if fwd.returncode == 0:
            return PatchStatus.CAN_APPLY
        return None

    # Try primary target first
    status = _try(target_dir)
    if status is not None:
        return status, target_dir

    # Fallback: workspace root, then ComfyUI root
    for fallback in (get_workspace_dir(), get_comfyui_dir()):
        if fallback == target_dir:
            continue
        status = _try(fallback)
        if status is not None:
            return status, fallback

    return PatchStatus.CONFLICT, target_dir


def apply_git_patch(patch_path: Path, target_dir: Path | None = None) -> bool:
    """Apply a single git patch idempotently. Returns True on success or already-applied."""
    if not _has_git():
        print("   [SKIP] git not found — skipping Category B patches.", file=sys.stderr)
        return False

    try:
        status, resolved_dir = check_git_patch(patch_path, target_dir)
    except RuntimeError as e:
        print(f"   [ERROR] {e}", file=sys.stderr)
        return False

    rel_patch = patch_path.relative_to(get_workspace_dir())

    if status == PatchStatus.APPLIED:
        print(f"   [OK] Git patch already applied: {rel_patch}")
        return True

    if status == PatchStatus.CAN_APPLY:
        res = subprocess.run(
            ["git", "apply", "--ignore-whitespace", str(patch_path.resolve())],
            cwd=resolved_dir,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            print(f"   [OK] Applied git patch: {rel_patch} -> {resolved_dir.name}")
            return True
        print(
            f"   [ERROR] Failed applying {rel_patch}: {res.stderr.strip()}",
            file=sys.stderr,
        )
        return False

    # CONFLICT
    print(
        f"   [WARN] Cannot apply git patch (conflict — upstream may have changed): {rel_patch}",
        file=sys.stderr,
    )
    return False


def revert_git_patch(patch_path: Path, target_dir: Path | None = None) -> bool:
    """Revert a single applied git patch. Returns True on success."""
    if not _has_git():
        print("   [SKIP] git not found — cannot revert patches.", file=sys.stderr)
        return False

    try:
        status, resolved_dir = check_git_patch(patch_path, target_dir)
    except RuntimeError as e:
        print(f"   [ERROR] {e}", file=sys.stderr)
        return False

    rel_patch = patch_path.relative_to(get_workspace_dir())

    if status == PatchStatus.CAN_APPLY:
        print(f"   [SKIP] Patch not applied (nothing to revert): {rel_patch}")
        return True

    if status == PatchStatus.APPLIED:
        res = subprocess.run(
            ["git", "apply", "--reverse", "--ignore-whitespace", str(patch_path.resolve())],
            cwd=resolved_dir,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            print(f"   [OK] Reverted git patch: {rel_patch} <- {resolved_dir.name}")
            return True
        print(
            f"   [ERROR] Failed reverting {rel_patch}: {res.stderr.strip()}",
            file=sys.stderr,
        )
        return False

    print(
        f"   [WARN] Cannot revert patch (conflict): {rel_patch}",
        file=sys.stderr,
    )
    return False


def apply_all_git_patches() -> tuple[int, list[Path]]:
    """Apply all Category B patches. Returns (success_count, conflict_list)."""
    if not _has_git():
        print("   [SKIP] git not found — skipping Category B patches.", file=sys.stderr)
        return 0, []

    patch_files = find_patch_files()
    if not patch_files:
        return 0, []

    success = 0
    conflicts: list[Path] = []
    for p in patch_files:
        if apply_git_patch(p):
            success += 1
        else:
            # apply_git_patch already checked status internally;
            # a failure that isn't "already applied" means conflict.
            conflicts.append(p)
    return success, conflicts


def revert_all_git_patches() -> int:
    """Revert all applied Category B patches. Returns count of successfully reverted."""
    if not _has_git():
        print("   [SKIP] git not found — cannot revert patches.", file=sys.stderr)
        return 0

    patch_files = find_patch_files()
    reverted = 0
    for p in patch_files:
        if revert_git_patch(p):
            reverted += 1
    return reverted


# ============================================================================
# Unified Orchestrator
# ============================================================================

def sync_dynamic_patches(report_conflicts: bool = False) -> tuple[int, list[Path]]:
    """Synchronize all patches: Category A links + Category B git patches.

    Args:
        report_conflicts: If True, return list of conflicting patch files for
                          caller to handle (e.g. `comfy update` post-reset).

    Returns:
        (total_active_count, conflict_list)
    """
    link_count = sync_dynamic_links()
    patch_count, conflicts = apply_all_git_patches()

    if report_conflicts and conflicts:
        print(
            f"\n   [WARNING] {len(conflicts)} git patch(es) could not be applied after update:",
            file=sys.stderr,
        )
        for c in conflicts:
            print(f"      - {c.relative_to(get_workspace_dir())}", file=sys.stderr)
        print(
            "   Run `comfy patch status` for details. Manual intervention may be required.\n",
            file=sys.stderr,
        )

    return link_count + patch_count, conflicts


def patch_status_summary() -> None:
    """Display comprehensive status of all patches."""
    patches_dir = get_patches_dir()
    if not patches_dir.exists() or not patches_dir.is_dir():
        print("\nNo patches/ directory found.")
        return

    comfyui_dir = get_comfyui_dir()

    # --- Category A ---
    cat_a_dirs = [d for d in patches_dir.iterdir() if _is_category_a_dir(d)]
    print("\n--- Dynamic Runtime Extensions (Category A: Symlink/Junction) ---")
    if not cat_a_dirs:
        print("  (None)")
    else:
        for p in sorted(cat_a_dirs):
            target_link = comfyui_dir / "custom_nodes" / p.name
            linked = target_link.exists()
            status = "[ACTIVE  (Linked)]" if linked else "[INACTIVE (Unlinked)]"
            print(f"  {status}  patches/{p.name}")

    # --- Category B ---
    print("\n--- Unified Diff Git Patches (Category B: git apply) ---")
    if not _has_git():
        print("  [SKIP] git not found on PATH.")
        return
    patch_files = find_patch_files()
    if not patch_files:
        print("  (None)")
    else:
        workspace_dir = get_workspace_dir()
        for p in patch_files:
            try:
                status, target_dir = check_git_patch(p)
                status_str = {
                    PatchStatus.APPLIED:    "[APPLIED          ]",
                    PatchStatus.CAN_APPLY:  "[UNAPPLIED (Ready)]",
                    PatchStatus.CONFLICT:   "[CONFLICT         ]",
                }.get(status, f"[{status}]")
                target_label = target_dir.name
            except RuntimeError as e:
                status_str = "[ERROR]"
                target_label = str(e)
            rel = p.relative_to(workspace_dir)
            print(f"  {status_str}  {rel}  (target: {target_label})")


if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "sync"
    if arg == "status":
        patch_status_summary()
    elif arg == "revert":
        revert_all_git_patches()
    else:
        sync_dynamic_patches()
