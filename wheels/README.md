# Pre-Built Linux Wheels for ComfyUI (Python 3.13 / PyTorch 2.14+ / CUDA 13.x)

This directory contains custom-built binary wheels for Linux, optimized for:
* **Python**: `==3.13.*`
* **PyTorch**: `2.14.0+cu132` (or compatible CUDA 13.x builds)
* **CUDA Toolchain**: CUDA 13.3 (`/opt/cuda`)
* **Target GPU Architecture**: NVIDIA RTX 5090 Blackwell (`sm_120a`) and Hopper/Ada (`sm_89`, `sm_90`)

---

## Included Wheels

1. **`sageattention-2.2.0-cp313-cp313-linux_x86_64.whl`** (from `thu-ml/SageAttention`)
   - High-performance quantized & fused attention kernels for ComfyUI.
2. **`spas_sage_attn-0.1.0-cp313-cp313-linux_x86_64.whl`** (from `woct0rdho/SpargeAttn`)
   - Sparse SageAttention backend required by custom nodes such as RadialAttn.

---

## Why Pre-Built Wheels are Required on Linux

### The Problem with Building from Git during `uv sync`
On Windows, `wrapper_config.toml` uses pre-compiled community wheels from GitHub releases, so `comfy.bat sync` never builds from source.
On Linux, however, there are no official pre-compiled wheels for Python 3.13 + PyTorch 2.14 + CUDA 13.3. When `uv sync` attempts to compile from Git:
1. **Isolated Build Sandbox**: `uv` creates an isolated build environment and downloads upstream PyTorch.
2. **C++20 Requirement in PyTorch 2.14**: PyTorch 2.14 C++ headers (`TensorBase.h:1031`) require C++20 concepts (`requires std::is_same_v<T, c10::SymInt>`), while upstream SageAttention and SpargeAttn hardcode `-std=c++17` in `setup.py`.
3. **GCC 15/16 Enforcements (CachyOS/Arch)**: Upstream PyTorch `List_inl.h:202` fails template deduction under GCC 15/16 when invoked by `nvcc`.

### The Solution
Build standalone binary wheels once with the required flags, and store them in this `wheels/` directory. `uv sync` installs these pre-built wheels in milliseconds with zero compiler invocations.

---

## How to Rebuild These Wheels (Automated)

Whenever you upgrade Python, PyTorch, or CUDA, simply run:

```bash
./scripts/build_attention_wheels.sh
```

The script will:
1. Locate the active virtual environment (`COMFY_VENV` or `.venv`).
2. Verify CUDA toolkit (`nvcc`) and GCC availability.
3. Automatically patch `setup.py` in both repositories to use `-std=c++20`.
4. Compile the CUDA kernels for RTX 5090 Blackwell (`sm_120a`) and Ada/Hopper.
5. Save the resulting `.whl` files directly into this `wheels/` folder.

---

## Manual Build Reference (If Rebuilding by Hand)

If you ever need to manually compile one of the packages:

```bash
# 1. Clone the repository
git clone --depth=1 https://github.com/thu-ml/SageAttention /tmp/SageAttention
cd /tmp/SageAttention

# 2. Patch setup.py to use C++20 (mandatory for PyTorch 2.14+)
sed -i 's/-std=c++17/-std=c++20/g' setup.py

# 3. Export CUDA paths
export CUDA_HOME=/opt/cuda
export PATH="/opt/cuda/bin:$PATH"

# 4. Build wheel using your virtual environment Python
$COMFY_VENV/bin/python setup.py bdist_wheel

# 5. Copy wheel to this directory
cp dist/*.whl ./wheels/
```
