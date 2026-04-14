#!/usr/bin/env bash
# ComfyUI Workspace Unified CLI
# Linux/macOS uses envs/linux/.venv
ENV_DIR="envs/linux"
# Use absolute workspace dir to avoid doubled-path bug when uv run changes cwd
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

export UV_PROJECT_ENVIRONMENT="${HOME}/envs_AIO/comfyUI_DATA1/.venv"
export VIRTUAL_ENV="${HOME}/envs_AIO/comfyUI_DATA1/.venv"
# UV_PYTHON overrides UV_PROJECT_ENVIRONMENT — unset it so uv uses the correct project env
unset UV_PYTHON

echo "Using environment: $ENV_DIR"

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
cd "$WORKSPACE_DIR/$ENV_DIR" && exec uv run python "../../scripts/cli.py" "$@"
