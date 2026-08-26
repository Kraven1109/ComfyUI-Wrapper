#!/bin/bash
# Build SageAttention and SpargeAttn wheels for Linux
# This script builds both attention libraries with CUDA support

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$WORKSPACE_DIR/build_wheels"
OUTPUT_DIR="$WORKSPACE_DIR/wheels_output"

echo "🔧 Building Attention Wheels for Linux"
echo "======================================="

# Create build directories
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"

# Check for CUDA
if ! command -v nvcc &> /dev/null; then
    echo "❌ Error: nvcc not found. CUDA toolkit must be installed."
    echo "   Set CUDA_HOME or add CUDA to PATH"
    exit 1
fi

CUDA_VERSION=$(nvcc --version | grep "release" | sed -n 's/.*release \([0-9.]*\).*/\1/p')
echo "✓ Found CUDA: $CUDA_VERSION"

# Set CUDA_HOME if not set
if [ -z "$CUDA_HOME" ]; then
    export CUDA_HOME=/opt/cuda
    echo "  Using CUDA_HOME=$CUDA_HOME"
fi

# Detect Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
echo "✓ Found Python: $PYTHON_VERSION"

# Install build dependencies
echo ""
echo "📦 Installing build dependencies..."
pip install --upgrade pip wheel setuptools auditwheel patchelf
pip install torch --index-url https://download.pytorch.org/whl/cu130

# Build SageAttention
echo ""
echo "🔨 Building SageAttention..."
cd "$BUILD_DIR"
if [ -d "SageAttention" ]; then
    rm -rf SageAttention
fi
git clone --depth=1 https://github.com/thu-ml/SageAttention
cd SageAttention
python setup.py bdist_wheel --verbose
mkdir -p "$OUTPUT_DIR/sageattention"
cp dist/*.whl "$OUTPUT_DIR/sageattention/"
echo "✓ SageAttention wheel created: $OUTPUT_DIR/sageattention/"

# Build SpargeAttn  
echo ""
echo "🔨 Building SpargeAttn..."
cd "$BUILD_DIR"
if [ -d "SpargeAttn" ]; then
    rm -rf SpargeAttn
fi
git clone --depth=1 https://github.com/thu-ml/SpargeAttn
cd SpargeAttn

# Workaround for GCC 15/glibc 2.42 header redefinition issue
# Remove the problematic -Xcompiler -include,cassert flag
if grep -q "\-Xcompiler \-include,cassert" setup.py; then
    echo "  Patching setup.py for GCC 15 compatibility..."
    sed -i 's/-Xcompiler -include,cassert//' setup.py
fi

python setup.py bdist_wheel --verbose
mkdir -p "$OUTPUT_DIR/spas_sage_attn"
cp dist/*.whl "$OUTPUT_DIR/spas_sage_attn/"
echo "✓ SpargeAttn wheel created: $OUTPUT_DIR/spas_sage_attn/"

# Summary
echo ""
echo "=========================================="
echo "✅ Build complete!"
echo ""
echo "Wheels saved to: $OUTPUT_DIR"
echo ""
echo "SageAttention:"
ls -lh "$OUTPUT_DIR/sageattention/"*.whl
echo ""
echo "SpargeAttn:"
ls -lh "$OUTPUT_DIR/spas_sage_attn/"*.whl
echo ""
echo "To install locally:"
echo "  pip install $OUTPUT_DIR/sageattention/*.whl"
echo "  pip install $OUTPUT_DIR/spas_sage_attn/*.whl"
echo ""
echo "To create a GitHub release:"
echo "  1. Create a new tag: git tag build-wheels-$(date +%Y%m%d)"
echo "  2. Push tag: git push origin build-wheels-$(date +%Y%m%d)"
echo "  3. Or manually upload wheels to GitHub Releases"
