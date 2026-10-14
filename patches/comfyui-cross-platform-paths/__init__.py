"""ComfyUI Dynamic Patch: Cross-Platform Universal Model Path Normalizer.

Eliminates cross-platform model path failures between Linux and Windows when
dual-booting or sharing workflows across different operating systems.

Key Architectural Guarantees:
1. Zero Blind Mutations: Uses Python's standard `pathlib.PureWindowsPath` combined
   with a model/media extension whitelist and key-context filters. Text prompts,
   Regex patterns (e.g. \\d+, \\w+), LaTeX, and escape characters are strictly protected.
2. Windows Drive Letter Rescue: Resolves paths containing Windows drive letters
   (e.g. D:\\AI\\models\\...) to local relative paths on Linux/macOS.
3. Universal Filesystem Gate: Normalizes `folder_paths.recursive_search` and
   `folder_paths.get_full_path` to use canonical POSIX forward slashes ('/')
   across all platforms.
4. Clean Architecture: Zero custom-node-specific hooks. Works universally across
   all nodes (rgthree, Impact Pack, Efficiency Nodes, etc.).
"""

from __future__ import annotations

import logging
from pathlib import Path, PureWindowsPath
from typing import Any

logger = logging.getLogger("ComfyUI-Cross-Platform-Paths")

# Model and media extensions tracked by ComfyUI
KNOWN_MODEL_EXTENSIONS = {
    ".safetensors",
    ".sft",
    ".ckpt",
    ".pt",
    ".pt2",
    ".pth",
    ".bin",
    ".gguf",
    ".ggml",
    ".bnb",
    ".yaml",
    ".json",
    ".pkl",
    ".onnx",
    ".ort",
    ".engine",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
}

PATH_KEY_HINTS = {
    "lora",
    "ckpt",
    "model",
    "file",
    "path",
    "name",
    "image",
    "video",
    "vae",
    "clip",
    "unet",
    "control_net",
    "diffusion",
}


def should_normalize_string(val: str, key_hint: str = "") -> bool:
    """Determine if a string represents a file/model path rather than a text prompt or regex."""
    if not isinstance(val, str) or ("\\" not in val and ":" not in val):
        return False

    try:
        p = PureWindowsPath(val)
        suffix = p.suffix.lower()

        # 1. Recognized model or media file extension
        if suffix in KNOWN_MODEL_EXTENSIONS:
            return True

        # 2. Key name strongly suggests a model/path AND string has folder separators
        k_lower = key_hint.lower() if key_hint else ""
        if any(hint in k_lower for hint in PATH_KEY_HINTS) and len(p.parts) > 1:
            return True
    except Exception:
        pass

    return False


def normalize_path_str(val: str) -> str:
    """Convert Windows path syntax to canonical POSIX format using PureWindowsPath."""
    try:
        p = PureWindowsPath(val)
        # If string has Windows drive letter (e.g. D:\models\...), extract path without drive
        if p.drive:
            # Return POSIX path (the filesystem gate will rescue it against folder_paths)
            return p.as_posix()
        return p.as_posix()
    except Exception:
        return val.replace("\\", "/")


def normalize_value(val: Any, key_hint: str = "") -> Any:
    """Recursively normalize paths in strings, dicts, lists, and tuples with context filters."""
    if isinstance(val, str):
        if should_normalize_string(val, key_hint):
            return normalize_path_str(val)
        return val
    elif isinstance(val, dict):
        return {k: normalize_value(v, key_hint=str(k)) for k, v in val.items()}
    elif isinstance(val, list):
        return [normalize_value(v, key_hint=key_hint) for v in val]
    elif isinstance(val, tuple):
        return tuple(normalize_value(v, key_hint=key_hint) for v in val)
    return val


def normalize_prompt_inputs(prompt: Any) -> Any:
    """Normalize file/model paths in all node inputs in a ComfyUI prompt dictionary."""
    if not isinstance(prompt, dict):
        return prompt

    for _, node_data in prompt.items():
        if isinstance(node_data, dict) and "inputs" in node_data and isinstance(node_data["inputs"], dict):
            for k, v in node_data["inputs"].items():
                node_data["inputs"][k] = normalize_value(v, key_hint=str(k))
    return prompt


def apply_patch() -> bool:
    success = True

    # 1. Hook folder_paths.recursive_search & folder_paths.get_full_path
    try:
        import folder_paths

        orig_recursive_search = folder_paths.recursive_search

        def patched_recursive_search(
            directory: str, excluded_dir_names: list[str] | None = None
        ) -> tuple[list[str], dict[str, float]]:
            result, dirs = orig_recursive_search(directory, excluded_dir_names=excluded_dir_names)
            # Universal forward slashes across all platforms
            result = [normalize_path_str(p) for p in result]
            return result, dirs

        folder_paths.recursive_search = patched_recursive_search

        orig_get_full_path = folder_paths.get_full_path

        def patched_get_full_path(folder_name: str, filename: str) -> str | None:
            if isinstance(filename, str):
                filename = normalize_path_str(filename)
                # If path contains a Windows drive letter (e.g. D:/AI/models/checkpoints/model.safetensors),
                # attempt to rescue it by searching tail path against local folder_paths
                p = PureWindowsPath(filename)
                if p.drive:
                    # Try matching relative sub-path against available files
                    available_files = folder_paths.get_filename_list(folder_name)
                    # Check progressively shorter tail segments
                    for i in range(1, len(p.parts)):
                        tail = "/".join(p.parts[i:])
                        if tail in available_files:
                            filename = tail
                            break
                    else:
                        # Fallback to pure filename
                        if p.name in available_files:
                            filename = p.name

                # Dual-boot case reconciliation: Windows NTFS is case-insensitive,
                # while Linux filesystems are case-sensitive. Auto-match matching casing.
                available_files = folder_paths.get_filename_list(folder_name)
                if filename not in available_files:
                    f_lower = filename.lower()
                    for cand in available_files:
                        if cand.lower() == f_lower:
                            filename = cand
                            break

            return orig_get_full_path(folder_name, filename)

        folder_paths.get_full_path = patched_get_full_path

        # Invalidate cached filename lists so fresh scans use normalized forward slashes
        if hasattr(folder_paths, "filename_list_cache") and isinstance(folder_paths.filename_list_cache, dict):
            folder_paths.filename_list_cache.clear()

        print("[OK] ComfyUI-Cross-Platform-Paths: folder_paths universal gate active.")
    except Exception as e:
        logger.error(f"[ComfyUI-Cross-Platform-Paths] Failed to hook folder_paths: {e}", exc_info=True)
        success = False

    # 2. Hook PromptServer on_prompt_handler (HTTP API Gate)
    try:
        import server

        def on_prompt_handler(json_data: dict) -> dict:
            if isinstance(json_data, dict) and "prompt" in json_data:
                json_data["prompt"] = normalize_prompt_inputs(json_data["prompt"])
            return json_data

        if hasattr(server, "PromptServer"):
            if hasattr(server.PromptServer, "instance") and server.PromptServer.instance:
                server.PromptServer.instance.add_on_prompt_handler(on_prompt_handler)
                print("[OK] ComfyUI-Cross-Platform-Paths: PromptServer HTTP API gate registered.")
            else:
                orig_init = server.PromptServer.__init__

                def patched_server_init(self, *args, **kwargs):
                    orig_init(self, *args, **kwargs)
                    self.add_on_prompt_handler(on_prompt_handler)

                server.PromptServer.__init__ = patched_server_init
                print("[OK] ComfyUI-Cross-Platform-Paths: PromptServer init gate registered.")
    except Exception as e:
        logger.warning(f"[ComfyUI-Cross-Platform-Paths] PromptServer hook deferred/skipped: {e}")

    # 3. Hook execution.validate_prompt (Engine / Direct Queue Gate)
    try:
        import execution

        orig_validate_prompt = execution.validate_prompt

        async def patched_validate_prompt(prompt_id: str, prompt: dict, partial_execution_list: list[str] | None):
            normalize_prompt_inputs(prompt)
            return await orig_validate_prompt(prompt_id, prompt, partial_execution_list)

        execution.validate_prompt = patched_validate_prompt
        print("[OK] ComfyUI-Cross-Platform-Paths: Engine validate_prompt gate active.")
    except Exception as e:
        logger.warning(f"[ComfyUI-Cross-Platform-Paths] execution.validate_prompt hook skipped: {e}")

    return success


apply_patch()

# Expose web directory for frontend extension
WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS: dict[str, Any] = {}
NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
