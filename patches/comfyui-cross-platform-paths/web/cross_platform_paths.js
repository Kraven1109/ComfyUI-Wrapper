import { app } from "../../scripts/app.js";

/**
 * Cross-Platform Universal Model Path Normalizer for ComfyUI Web Frontend.
 *
 * Uses smart extension and widget filtering to protect text prompts,
 * LaTeX, and Regex patterns from accidental mutation.
 */

const KNOWN_MODEL_EXTENSIONS = new Set([
    ".safetensors", ".sft", ".ckpt", ".pt", ".pt2", ".pth", ".bin",
    ".gguf", ".ggml", ".bnb", ".yaml", ".json", ".pkl", ".onnx", ".ort",
    ".engine", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov",
    ".avi", ".mkv", ".webm"
]);

const PATH_KEY_HINTS = new Set([
    "lora", "ckpt", "model", "file", "path", "name", "image", "video",
    "vae", "clip", "unet", "control_net", "diffusion"
]);

function shouldNormalizeString(val, keyHint = "") {
    if (typeof val !== "string" || !val.includes("\\")) {
        return false;
    }

    const lower = val.toLowerCase();
    for (const ext of KNOWN_MODEL_EXTENSIONS) {
        if (lower.endsWith(ext)) {
            return true;
        }
    }

    if (keyHint) {
        const kLower = keyHint.toLowerCase();
        for (const hint of PATH_KEY_HINTS) {
            if (kLower.includes(hint) && val.includes("\\")) {
                return true;
            }
        }
    }

    return false;
}

function normalizeRecursive(val, keyHint = "") {
    if (typeof val === "string") {
        return shouldNormalizeString(val, keyHint) ? val.replace(/\\/g, "/") : val;
    }
    if (Array.isArray(val)) {
        for (let i = 0; i < val.length; i++) {
            val[i] = normalizeRecursive(val[i], keyHint);
        }
        return val;
    }
    if (val && typeof val === "object") {
        for (const [k, v] of Object.entries(val)) {
            val[k] = normalizeRecursive(v, k);
        }
        return val;
    }
    return val;
}

app.registerExtension({
    name: "ComfyUI.CrossPlatformPaths",

    async beforeConfigureGraph(graphData) {
        if (!graphData || !Array.isArray(graphData.nodes)) {
            return;
        }

        let count = 0;
        for (const node of graphData.nodes) {
            // Never touch pure text nodes like CLIPTextEncode
            if (node.type === "CLIPTextEncode" || node.type?.includes?.("Text")) {
                continue;
            }

            if (node.widgets_values !== undefined) {
                node.widgets_values = normalizeRecursive(node.widgets_values);
                count++;
            }
        }

        if (count > 0) {
            console.log(`[CrossPlatformPaths] Safe path check completed across ${count} node(s).`);
        }
    },

    async nodeCreated(node) {
        if (node?.type === "CLIPTextEncode" || node?.type?.includes?.("Text")) {
            return;
        }

        if (node?.widgets) {
            for (const widget of node.widgets) {
                // Only normalize combo dropdowns or widgets with path hints
                if (widget.type === "combo" || shouldNormalizeString(widget.value, widget.name)) {
                    widget.value = normalizeRecursive(widget.value, widget.name);
                }
            }
        }
    },

    async setup() {
        const origGraphToPrompt = app.graphToPrompt;
        app.graphToPrompt = async function (...args) {
            const res = await origGraphToPrompt.apply(this, args);
            if (res?.output && typeof res.output === "object") {
                for (const node of Object.values(res.output)) {
                    if (node?.class_type === "CLIPTextEncode") {
                        continue;
                    }
                    if (node?.inputs && typeof node.inputs === "object") {
                        node.inputs = normalizeRecursive(node.inputs);
                    }
                }
            }
            return res;
        };
        console.log("[CrossPlatformPaths] Web frontend safe path hook initialized.");
    }
});
