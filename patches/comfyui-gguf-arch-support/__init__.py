"""ComfyUI Dynamic Patch: Extended Architecture Support for ComfyUI-GGUF.

Enables loading of newer and un-tagged diffusion architectures in ComfyUI-GGUF,
specifically resolving:
- 'Unknown model architecture!' on Qwen-Image-2.1 (released Sep 20 2026) and Qwen-Image 1.0
- GGUF files created without 'general.architecture' metadata (compat mode 'sd.cpp')
- Missing architectures in IMG_ARCH_LIST (e.g. qwen_image21, minimax, krea2, ideogram4)
- Safe fallback to ComfyUI Core's native model_detection if GGUF detection misses.

Implements Category A Dynamic Runtime Extension (zero modification to upstream ComfyUI-GGUF).
"""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Optional, Set, Tuple

logger = logging.getLogger("ComfyUI-GGUF-Arch-Support")

# Additional architectures to support
EXTENDED_IMG_ARCHS: Set[str] = {
    "qwen_image",
    "qwen_image21",
    "minimax",
    "krea2",
    "ideogram4",
}


def _find_gguf_loader_modules() -> list[Any]:
    """Locate any loaded ComfyUI-GGUF loader modules in sys.modules."""
    loaders = []
    for mod_name, mod in list(sys.modules.items()):
        if mod is None:
            continue
        if ("ComfyUI-GGUF" in mod_name or "ComfyUI_GGUF" in mod_name) and hasattr(mod, "IMG_ARCH_LIST"):
            loaders.append(mod)
    return loaders


def _find_gguf_convert_modules() -> list[Any]:
    """Locate any loaded ComfyUI-GGUF convert modules in sys.modules."""
    converts = []
    for mod_name, mod in list(sys.modules.items()):
        if mod is None:
            continue
        if ("ComfyUI-GGUF" in mod_name or "ComfyUI_GGUF" in mod_name) and hasattr(mod, "arch_list"):
            converts.append(mod)
    return converts


def _patch_loader_module(loader_mod: Any) -> bool:
    """Add extended architectures to IMG_ARCH_LIST in loader.py."""
    if hasattr(loader_mod, "IMG_ARCH_LIST"):
        current_archs = getattr(loader_mod, "IMG_ARCH_LIST")
        if isinstance(current_archs, set):
            before_len = len(current_archs)
            current_archs.update(EXTENDED_IMG_ARCHS)
            if len(current_archs) > before_len:
                logger.info(f"Updated IMG_ARCH_LIST with {EXTENDED_IMG_ARCHS}")
            return True
    return False


def _patch_convert_module(convert_mod: Any, loader_mod: Optional[Any] = None) -> bool:
    """Add model templates and robust fallback detection to tools/convert.py."""
    if not hasattr(convert_mod, "arch_list") or not hasattr(convert_mod, "ModelTemplate"):
        return False

    arch_list = getattr(convert_mod, "arch_list")
    ModelTemplate = getattr(convert_mod, "ModelTemplate")
    existing_arch_names = {getattr(a, "arch", "") for a in arch_list}

    # Define Qwen Image 2.1 detector (released Sep 20, 2026)
    # Distinguishing key: 'txt_in.text_norm.weight' (differs from Qwen-Image 1.0 'txt_norm.weight')
    if "qwen_image21" not in existing_arch_names:
        class QwenImage21(ModelTemplate):
            arch = "qwen_image21"
            keys_detect = [
                ("txt_in.text_norm.weight",),
                ("transformer_blocks.0.img_mlp.proj.weight",),
                ("transformer_blocks.0.img_mlp.gate_layer.weight",),
            ]
        arch_list.append(QwenImage21)
        logger.info("Registered QwenImage21 in convert.arch_list")

    # Define Qwen Image 1.0 detector
    if "qwen_image" not in existing_arch_names:
        class ModelQwenImage(ModelTemplate):
            arch = "qwen_image"
            keys_detect = [
                ("txt_norm.weight",),
            ]
        arch_list.append(ModelQwenImage)
        logger.info("Registered ModelQwenImage in convert.arch_list")

    # Define MiniMax detector
    if "minimax" not in existing_arch_names:
        class ModelMiniMax(ModelTemplate):
            arch = "minimax"
            keys_detect = [
                ("video_patch_proj.weight", "audio_patch_proj.weight"),
            ]
        arch_list.append(ModelMiniMax)

    # Define Krea2 detector
    if "krea2" not in existing_arch_names:
        class ModelKrea2(ModelTemplate):
            arch = "krea2"
            keys_detect = [
                ("txtfusion.projector.weight",),
                ("text_fusion.projector.weight",),
            ]
        arch_list.append(ModelKrea2)

    # Define Ideogram4 detector
    if "ideogram4" not in existing_arch_names:
        class ModelIdeogram4(ModelTemplate):
            arch = "ideogram4"
            keys_detect = [
                ("embed_image_indicator.weight",),
            ]
        arch_list.append(ModelIdeogram4)

    # Wrap detect_arch with smart fallback to ComfyUI Core model detection
    orig_detect_arch = getattr(convert_mod, "detect_arch", None)
    if orig_detect_arch and not getattr(orig_detect_arch, "_is_patched_fallback", False):
        def robust_detect_arch(state_dict: Any) -> Any:
            try:
                return orig_detect_arch(state_dict)
            except Exception as original_err:
                keys = set(state_dict.keys()) if isinstance(state_dict, dict) else set(state_dict)
                # 1. Direct check for Qwen-Image 2.1
                if "txt_in.text_norm.weight" in keys or any("img_mlp" in k for k in keys):
                    class FallbackQwen21:
                        arch = "qwen_image21"
                    if loader_mod and hasattr(loader_mod, "IMG_ARCH_LIST"):
                        loader_mod.IMG_ARCH_LIST.add("qwen_image21")
                    return FallbackQwen21()

                # 2. Direct check for Qwen-Image 1.0
                if "txt_norm.weight" in keys:
                    class FallbackQwen:
                        arch = "qwen_image"
                    if loader_mod and hasattr(loader_mod, "IMG_ARCH_LIST"):
                        loader_mod.IMG_ARCH_LIST.add("qwen_image")
                    return FallbackQwen()

                # 3. ComfyUI Core model detection fallback
                try:
                    import comfy.model_detection
                    fake_sd = {k: None for k in keys} if not isinstance(state_dict, dict) else state_dict
                    detected = comfy.model_detection.detect_unet_config(fake_sd, "")
                    if detected and "image_model" in detected:
                        arch_id = detected["image_model"]
                        logger.info(f"Fallback detection identified architecture: {arch_id}")
                        if loader_mod and hasattr(loader_mod, "IMG_ARCH_LIST"):
                            loader_mod.IMG_ARCH_LIST.add(arch_id)
                        class FallbackCoreArch:
                            arch = arch_id
                        return FallbackCoreArch()
                except Exception as core_err:
                    logger.debug(f"ComfyUI core model detection fallback error: {core_err}")

                raise original_err

        robust_detect_arch._is_patched_fallback = True  # type: ignore[attr-defined]
        convert_mod.detect_arch = robust_detect_arch
        logger.info("Wrapped convert.detect_arch with robust ComfyUI core fallback")

    return True


def apply_patch() -> bool:
    """Apply dynamic runtime patches to ComfyUI-GGUF modules."""
    try:
        # 1. Patch any already loaded loader modules
        loader_mods = _find_gguf_loader_modules()
        for l_mod in loader_mods:
            _patch_loader_module(l_mod)
            # Proactively import and patch tools.convert via loader's package
            pkg = getattr(l_mod, "__package__", None)
            if pkg:
                try:
                    convert_mod = importlib.import_module(f"{pkg}.tools.convert")
                    _patch_convert_module(convert_mod, l_mod)
                except Exception as imp_err:
                    logger.debug(f"Could not proactively import convert from {pkg}: {imp_err}")

        # 2. Patch any already loaded convert modules
        for c_mod in _find_gguf_convert_modules():
            _patch_convert_module(c_mod, loader_mods[0] if loader_mods else None)

        # 3. Hook nodes.NODE_CLASS_MAPPINGS["UnetLoaderGGUF"] to guarantee runtime enforcement
        try:
            import nodes as comfy_nodes
            unet_loader_cls = comfy_nodes.NODE_CLASS_MAPPINGS.get("UnetLoaderGGUF")
            if unet_loader_cls and not getattr(unet_loader_cls.load_unet, "_is_arch_patched", False):
                orig_load_unet = unet_loader_cls.load_unet

                def patched_load_unet(self: Any, unet_name: str, **kwargs: Any) -> Any:
                    # Enforce patch before loading
                    active_loaders = _find_gguf_loader_modules()
                    for lm in active_loaders:
                        _patch_loader_module(lm)
                        pkg = getattr(lm, "__package__", None)
                        if pkg:
                            try:
                                c_mod = importlib.import_module(f"{pkg}.tools.convert")
                                _patch_convert_module(c_mod, lm)
                            except Exception:
                                pass

                    for cm in _find_gguf_convert_modules():
                        _patch_convert_module(cm, active_loaders[0] if active_loaders else None)

                    return orig_load_unet(self, unet_name, **kwargs)

                patched_load_unet._is_arch_patched = True  # type: ignore[attr-defined]
                unet_loader_cls.load_unet = patched_load_unet
                logger.info("Hooked UnetLoaderGGUF.load_unet for execution-time patch enforcement")
        except Exception as node_err:
            logger.debug(f"Could not hook UnetLoaderGGUF directly: {node_err}")

        print("[OK] ComfyUI-GGUF-Arch-Support dynamic patch loaded successfully.")
        return True
    except Exception as e:
        logger.warning(f"Failed to apply ComfyUI-GGUF-Arch-Support patch: {e}", exc_info=True)
        return False


apply_patch()

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
