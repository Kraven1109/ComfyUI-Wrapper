#!/usr/bin/env bash
# ComfyUI Workspace Unified CLI
# Linux/macOS uses envs/linux/.venv
ENV_DIR="envs/linux"
# Use absolute workspace dir (resolves symlinks so comfy can be invoked via PATH or symlinks)
SCRIPT_SOURCE="$(readlink -f "${BASH_SOURCE[0]:-$0}" 2>/dev/null || realpath "${BASH_SOURCE[0]:-$0}" 2>/dev/null || echo "${BASH_SOURCE[0]:-$0}")"
WORKSPACE_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"

# --- Environment & Hardlink Source of Truth ---
export COMFY_VENV="${COMFY_VENV:-${HOME}/envs_AIO/comfyUI_DATA1/.venv}"
export UV_PROJECT_ENVIRONMENT="$COMFY_VENV"
export VIRTUAL_ENV="$COMFY_VENV"
export UV_CACHE_DIR="${UV_CACHE_DIR:-${HOME}/.cache/uv}"
export UV_LINK_MODE=hardlink
# UV_PYTHON overrides UV_PROJECT_ENVIRONMENT — unset it so uv uses the correct project env
unset UV_PYTHON

echo "Using environment: $ENV_DIR"
echo "Using venv:        $COMFY_VENV"
echo "Using cache:       $UV_CACHE_DIR"

# CUDA environment configuration
if [ -d "/opt/cuda" ]; then
    export CUDA_HOME="/opt/cuda"
    export PATH="/opt/cuda/bin:$PATH"
    export LD_LIBRARY_PATH="/opt/cuda/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

# GCC 15 toolchain shim for PyTorch & CUDA extension compatibility
if [ -d "$WORKSPACE_DIR/.tools/gcc15" ]; then
    export PATH="$WORKSPACE_DIR/.tools/gcc15:$PATH"
    export CUDAHOSTCXX="$WORKSPACE_DIR/.tools/gcc15/g++"
    export CC="$WORKSPACE_DIR/.tools/gcc15/gcc"
    export CXX="$WORKSPACE_DIR/.tools/gcc15/g++"
fi
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv &> /dev/null; then
    echo "[INFO] uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "[INFO] uv installed. Re-run the script."
    exit 0
fi

CUSTOM_NODES_DIR="$WORKSPACE_DIR/ComfyUI/custom_nodes"
mkdir -p "$CUSTOM_NODES_DIR"

# ── Auto-symlink custom node projects ──────────────────────────────────────
# Always recreate symlinks so stale cross-platform links (e.g. Windows d:/ paths)
# are automatically replaced. ln -sfn replaces an existing symlink atomically.
declare -A CUSTOM_NODES=(
    ["ComfyUI-LLama"]="/DATA1/quang_dev/ComfyUI-LLama"
    ["ComfyUI-TTSS"]="/DATA1/quang_dev/comfyUI-TTSS"
)
for NODE_NAME in "${!CUSTOM_NODES[@]}"; do
    SRC="${CUSTOM_NODES[$NODE_NAME]}"
    DEST="$CUSTOM_NODES_DIR/$NODE_NAME"
    if [ ! -e "$SRC" ]; then
        echo "[WARN] Source not found, skipping: $SRC"
    else
        ln -sfn "$SRC" "$DEST"
        echo "[OK] Symlinked: $NODE_NAME → $SRC"
    fi
done
# ───────────────────────────────────────────────────────────────────────────

# ── Auto-symlink model directories ─────────────────────────────────────────
declare -A MODEL_DIRS=(
    ["LLM"]="/DATA2/llm/models"
)
MODELS_DIR="$WORKSPACE_DIR/ComfyUI/models"
for MODEL_NAME in "${!MODEL_DIRS[@]}"; do
    SRC="${MODEL_DIRS[$MODEL_NAME]}"
    DEST="$MODELS_DIR/$MODEL_NAME"
    if [ ! -e "$SRC" ]; then
        echo "[WARN] Model source not found, skipping: $SRC"
    else
        ln -sfn "$SRC" "$DEST"
        echo "[OK] Model dir symlinked: $MODEL_NAME → $SRC"
    fi
done
# ───────────────────────────────────────────────────────────────────────────

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd "$WORKSPACE_DIR/$ENV_DIR" && exec uv run --no-sync python "../../scripts/cli.py" "$@"
