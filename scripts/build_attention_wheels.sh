#!/bin/bash
# Build SageAttention and SpargeAttn wheels for Linux
# Builds both attention libraries with CUDA support and sm_120a / Ada / Hopper architecture
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$WORKSPACE_DIR/build_wheels"
WHEELS_DIR="$WORKSPACE_DIR/wheels"

echo "🔧 Building Attention Wheels for Linux"
echo "======================================="

mkdir -p "$BUILD_DIR"
mkdir -p "$WHEELS_DIR"

# Check for CUDA
if ! command -v nvcc &> /dev/null; then
    if [ -x "/opt/cuda/bin/nvcc" ]; then
        export PATH="/opt/cuda/bin:$PATH"
    else
        echo "❌ Error: nvcc not found. CUDA toolkit must be installed."
        exit 1
    fi
fi

export CUDA_HOME="${CUDA_HOME:-/opt/cuda}"
CUDA_VERSION=$(nvcc --version | grep "release" | sed -n 's/.*release \([0-9.]*\).*/\1/p')
echo "✓ Found CUDA: $CUDA_VERSION (CUDA_HOME=$CUDA_HOME)"

# Detect Python (prefer active venv or COMFY_VENV)
if [ -n "$COMFY_VENV" ] && [ -x "$COMFY_VENV/bin/python" ]; then
    PYTHON="$COMFY_VENV/bin/python"
elif [ -x "$WORKSPACE_DIR/.venv/bin/python" ]; then
    PYTHON="$WORKSPACE_DIR/.venv/bin/python"
elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python"
else
    PYTHON="$(command -v python3 || command -v python)"
fi

echo "✓ Using Python: $($PYTHON --version) ($PYTHON)"

# Ensure build requirements in python
$PYTHON -c "import torch; print(f'✓ PyTorch: {torch.__version__} (CUDA available: {torch.cuda.is_available()})')" || {
    echo "❌ Error: PyTorch is required in the build environment."
    exit 1
}

# 1. Build SageAttention
echo ""
echo "🔨 Building SageAttention..."
cd "$BUILD_DIR"
rm -rf SageAttention
git clone --depth=1 https://github.com/thu-ml/SageAttention
cd SageAttention

# Patch setup.py for C++20 (mandatory for PyTorch 2.14+)
sed -i 's/-std=c++17/-std=c++20/g' setup.py

$PYTHON setup.py bdist_wheel
cp dist/*.whl "$WHEELS_DIR/"
echo "✓ SageAttention wheel saved to: $WHEELS_DIR/"

# 2. Build SpargeAttn
echo ""
echo "🔨 Building SpargeAttn..."
cd "$BUILD_DIR"
rm -rf SpargeAttn
# Use woct0rdho fork - includes sm_120a / Blackwell support and modern glibc compatibility
git clone --depth=1 https://github.com/woct0rdho/SpargeAttn
cd SpargeAttn

# Patch setup.py for C++20 (mandatory for PyTorch 2.14+)
sed -i 's/-std=c++17/-std=c++20/g' setup.py

$PYTHON setup.py bdist_wheel
cp dist/*.whl "$WHEELS_DIR/"
echo "✓ SpargeAttn wheel saved to: $WHEELS_DIR/"

echo ""
echo "=========================================="
echo "✅ Build complete! Wheels available at:"
ls -lh "$WHEELS_DIR/"*.whl
