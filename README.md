# ComfyUI Portable Workspace

Modern, maintainable ComfyUI workspace with unified Python scripts, hardware acceleration, and cross-platform isolation.

## ⚡ Quick Start

### Windows
```cmd
comfy.bat run sage          REM Run with SageAttention 2.2+ (Default)
comfy.bat update            REM Update upstream ComfyUI + auto-sync
comfy.bat sync              REM Regenerate wrapper (auto locks & syncs)
```

### Linux/macOS
```bash
./comfy.sh sync             # Auto-detects Linux, generates env & installs platform packages
./comfy.sh run sage         # Run with SageAttention
```

> **Note**: `comfy sync` automatically detects platform, sets PyTorch CUDA indices, and manages dependencies!

---

## 🔄 Cross-Platform Isolation Architecture (Windows ↔ Linux)

Each operating system maintains an independent, isolated resolution environment to prevent cross-OS binary wheel conflicts:

```
ComfyUI_portable/
├── comfy.bat / comfy.sh              # Unified CLI Entrypoints (Windows / Linux)
├── wrapper_config.toml               # Single Source of Truth for PyTorch, deps & wheels
├── backups/                          # Centralized environment snapshot storage
├── logs/                             # Centralized runtime logs (auto-rotated every 30 days)
├── envs/
│   ├── windows/                      # Windows environment (pyproject.toml, uv.lock)
│   └── linux/                        # Linux environment (pyproject.toml, uv.lock)
├── scripts/                          # Cross-platform automation scripts
│   ├── cli.py                        # Unified CLI dispatcher
│   ├── common.py                     # Shared paths, platform detection, log rotation
│   ├── run_comfy.py                  # ComfyUI launcher with attention modes
│   ├── sync_wrapper.py               # Dual-platform pyproject generator
│   ├── update_comfy.py               # Upstream sync & git updater
│   ├── backup_env.py                 # Snapshot generator (saves to backups/)
│   └── restore_env.py                # Snapshot restorer (reads from backups/)
└── ComfyUI/                          # ComfyUI backend engine (isolated git repository)
    ├── custom_nodes/                 # Extensions (Junctions to dev projects)
    ├── models/                       # Models & symlinks (checkpoints, VAE, etc.)
    └── user/default/workflows/       # Canonical directory for all workflow DAG JSONs
```

### When switching platforms:
- **Windows to Linux:** `./comfy.sh sync` → `./comfy.sh run sage`
- **Linux to Windows:** `comfy.bat sync` → `comfy.bat run sage`

### Platform Differences (automatically handled):
- **Windows (`envs/windows/`)**:
  - SageAttention 2.2.0.post4 (stable ABI, CUDA 13.0/13.2 pre-built wheel)
  - SpargeAttn 0.1.0.post4 for RadialAttn (Windows wheel)
  - decord2 3.0.0 pre-built wheel with bundled FFmpeg
  - triton-windows for JIT compilation
  - insightface Python 3.13 pre-built wheel
- **Linux/macOS (`envs/linux/`)**:
  - SageAttention >=2.2.0 (pre-built Linux wheel in `wheels/` with CUDA 13.x & Blackwell/Ada/Hopper support)
  - SpargeAttn >=0.1.0 for RadialAttn (pre-built Linux wheel in `wheels/`)
  - decord2 >=3.0.0 from PyPI
  - soundfile from PyPI

---

## ⚙️ Configuration (`wrapper_config.toml`)

All dependencies, PyTorch CUDA wheel channels, and platform-specific packages are configured in [wrapper_config.toml](wrapper_config.toml):

```toml
# PyTorch CUDA index configuration
[pytorch]
index_name = "pytorch-cu132"
index_url = "https://download.pytorch.org/whl/cu132"
torchaudio_index_name = "pytorch-test-cu132"
torchaudio_index_url = "https://download.pytorch.org/whl/test/cu132"

# Universal custom node dependencies (common to all platforms)
[dependencies]
custom = [
    "comfyui-manager",
    "opencv-python",
    "accelerate",
    "numpy>=2.0.0",
    "soundfile",
    "edge-tts",
    "kokoro-onnx",
    "snac",
    # ...
]

# Windows-only wheels & ABI3 overrides
[dependencies.windows]
python = "==3.13.*"
insightface = "https://github.com/Gourieff/Assets/raw/main/Insightface/insightface-0.7.3-cp313-cp313-win_amd64.whl"
sageattention = "https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post4/sageattention-2.2.0%2Bcu130torch2.9.0andhigher.post4-cp39-abi3-win_amd64.whl"
spas-sage-attn = "https://github.com/woct0rdho/SpargeAttn/releases/download/v0.1.0-windows.post4/spas_sage_attn-0.1.0%2Bcu130torch2.9.0andhigher.post4-cp39-abi3-win_amd64.whl"
triton-windows = ">=3.6.0"
decord2 = "https://github.com/Kraven1109/ComfyUI-Wrapper/releases/download/v3.0.0-decord2/decord2-3.0.0%2Bwin.x64.cpu-py3-none-any.whl"

# Linux/macOS-only dependencies
[dependencies.linux]
python = ">=3.11"
insightface = ">=0.7.3"
decord2 = ">=3.0.0"
```

After editing `wrapper_config.toml`, simply run:
```bash
comfy.bat sync      # Windows
./comfy.sh sync     # Linux
```

---

## 🛠️ CLI Commands & Workflows

### Unified CLI
```bash
comfy run [mode] [args]      # Run ComfyUI (modes: sage, flash, pytorch, split, quad, none)
comfy update                 # Update upstream ComfyUI + auto-sync environment
comfy backup                 # Create snapshot in backups/
comfy restore [backup]       # Restore environment from backups/
comfy sync                   # Regenerate wrapper + lock + sync (all automated!)
comfy help                   # Show help message
```

### Attention Modes
- `sage` - SageAttention 2.2+ (Default, fastest on modern NVIDIA GPUs)
- `flash` - FlashAttention2
- `pytorch` - PyTorch native SDPA
- `split` - Split cross-attention (low VRAM)
- `quad` - Quad cross-attention
- `none` - No attention flags

### Environment Backup & Restore
All snapshots are stored in the centralized [backups/](backups/) directory:
```bash
# Create a new backup
comfy.bat backup

# Restore from latest backup
comfy.bat restore

# Restore from a specific dated snapshot in backups/
comfy.bat restore uv.lock.backup_20260826_095818
```

### Centralized Logs & Auto-Rotation
Runtime logs are stored in [logs/](logs/). Every execution of `comfy run` automatically scans and deletes log files older than 30 days (`rotate_logs(30)`).
