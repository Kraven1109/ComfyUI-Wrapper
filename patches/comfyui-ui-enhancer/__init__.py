"""ComfyUI UI Enhancer - Dynamic Runtime UI & Theme Patch.

Stored inside patches/ and dynamically symlinked into ComfyUI/custom_nodes/
at runtime. If removed from patches/, it is automatically unlinked and not loaded.
"""

WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
