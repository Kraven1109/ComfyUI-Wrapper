# ComfyUI Portable Workspace

Modern, maintainable ComfyUI workspace with unified Python scripts and cross-platform support.

## ⚡ Quick Start

### Windows
```cmd
comfy.bat run sage          REM Run with SageAttention 2.2
comfy.bat update            REM Update ComfyUI + dependencies
comfy.bat sync              REM Regenerate wrapper (auto locks & syncs)
```

### Linux/macOS
```bash
./comfy.sh sync             # Auto-detects Linux, installs platform-specific packages
./comfy.sh run sage         # Run with SageAttention
```

> **Note**: `sync` now auto-detects platform and installs decord2 + sageattention automatically!

## 🔄 Cross-Platform Usage (Windows ↔ Linux)

**Platform-specific environments** - each platform has its own independent environment:

**Directory Structure:**
```
ComfyUI_portable/
├── envs/
│   ├── windows/              # Windows environment
│   │   ├── .venv/            # Windows Python virtual environment
│   │   ├── pyproject.toml    # Windows-specific dependencies
│   │   └── uv.lock           # Windows dependency lock
│   └── linux/                # Linux/macOS environment
│       ├── .venv/            # Linux Python virtual environment
│       ├── pyproject.toml    # Linux-specific dependencies
│       └── uv.lock           # Linux dependency lock
├── wrapper_config.toml       # Shared configuration
├── comfy.bat                 # Windows launcher → uses envs/windows/
└── comfy.sh                  # Linux launcher → uses envs/linux/
```

**When switching platforms:**

1. **Windows to Linux:**
   ```bash
   ./comfy.sh sync         # Syncs envs/linux/ with Linux-specific packages
   ./comfy.sh run sage     # Uses envs/linux/.venv
   ```

2. **Linux to Windows:**
   ```cmd
   comfy.bat sync          # Syncs envs/windows/ with Windows-specific packages
   comfy.bat run sage      # Uses envs/windows/.venv
   ```

**Platform Differences (automatically handled):**
- **Windows** (`envs/windows/`):
  - SageAttention 2.2.0.post4 from woct0rdho wheel (stable ABI, CUDA 13.0)
  - SpargeAttn 0.1.0.post4 for RadialAttn (sparse attention, Windows wheel)
  - decord2 3.0.0 pre-built wheel from GitHub release (FFmpeg bundled)
  - triton-windows for JIT compilation
  - soundfile for audio processing
- **Linux/macOS** (`envs/linux/`):
  - SageAttention >=2.2.0 (builds from source with CUDA support)
  - decord2 >=3.0.0 from PyPI (Linux/macOS wheels)
  - soundfile from PyPI

**Benefits:**
- ✅ **No dependency conflicts** - Windows and Linux wheels don't interfere
- ✅ **Platform isolation** - Each OS manages its own environment
- ✅ **Reproducible** - Lock files are platform-specific
- ✅ **Git-friendly** - Environments excluded from git (.venv/ in .gitignore)

## 🆕 What's New (February 2026)

### SageAttention 2.2.0.post4 Installed
- **Version**: 2.2.0+cu130torch2.9.0andhigher.post4  
- **Source**: [woct0rdho/SageAttention](https://github.com/woct0rdho/SageAttention) (Windows optimized fork)
- **Features**:
  - ✅ Supports PyTorch 2.9+ (including 2.10.0)
  - ✅ Python ABI3 (works with Python 3.9+)
  - ✅ `torch.compile` support for full-graph compilation
  - ✅ CUDA 13.0 compatible
  - ✅ 2-5× faster than FlashAttention2 on supported GPUs
- **Improvements over 1.0.6**:
  - CUDA backend (not just Triton) with INT8+FP16/FP8 quantization
  - Better accuracy with per-block quantization  
  - Support for GQA, variable sequence lengths, causal masking

## ⚙️ Configuration

**Edit [wrapper_config.toml](wrapper_config.toml) for all customizations:**

```toml
# Change PyTorch CUDA version
[pytorch]
index_name = "pytorch-cu130"  # cu121, cu124, etc.
index_url = "https://download.pytorch.org/whl/cu130"

# Common dependencies (all platforms)
[dependencies]
custom = [
    "comfyui-manager>=4.0.5",
    "opencv-python",
    # ... add your packages here
]

# Windows-only dependencies
[dependencies.windows]
sageattention = "https://github.com/woct0rdho/.../wheel.whl"

# Linux/macOS-only dependencies  
[dependencies.linux]
decord2 = ">=3.0.0"
sageattention = ">=2.2.0"
```

After editing config:
```bash
./comfy.sh sync              # Auto-detects platform, regenerates pyproject.toml, locks & syncs
```

No need to chain commands - `comfy sync` does everything automatically!

## Architecture

```
ComfyUI_portable/
├── comfy.sh / comfy.bat      # Unified CLI (main interface)
├── wrapper_config.toml       # ← Edit this for all customizations
│
├── envs/                     # Platform-specific environments
│   ├── windows/              # Windows environment (used by comfy.bat)
│   │   ├── .venv/            # Virtual environment (not in git)
│   │   ├── pyproject.toml    # Auto-generated for Windows
│   │   └── uv.lock           # Windows dependency lock
│   └── linux/                # Linux environment (used by comfy.sh)
│       ├── .venv/            # Virtual environment (not in git)
│       ├── pyproject.toml    # Auto-generated for Linux
│       └── uv.lock           # Linux dependency lock
│
├── scripts/                  # Python implementation (cross-platform)
│   ├── cli.py                # Unified CLI dispatcher
│   ├── common.py             # Shared utilities (detects platform env dir)
│   ├── run_comfy.py          # Run ComfyUI
│   ├── update_comfy.py       # Update workflow
│   ├── backup_env.py         # Backup environment
│   ├── restore_env.py        # Restore environment
│   └── sync_wrapper.py       # Generate BOTH platform pyproject.toml files
│
└── ComfyUI/                  # Git repository (clean, auto-updated)
    ├── pyproject.toml        # Upstream metadata
    ├── requirements.txt      # Upstream dependencies
    └── comfy/ldm/lightricks/model.py  # Patched for MagCache compatibility
```

## Why This Design?

### ✅ Advantages

1. **Single source of truth**: One config file ([wrapper_config.toml](wrapper_config.toml))
2. **Maintainable**: All logic in Python scripts, not duplicated shell/batch
3. **Cross-platform**: Same Python code runs on Linux/Windows/Mac
4. **Git-safe**: Environment at parent level, never touched by `git reset`
5. **Reproducible**: Locked dependencies with exact versions + hashes
6. **Auto-sync**: Updates from upstream requirements.txt automatically

### 🎯 vs Traditional Setup

| Feature | pip + venv | This Workspace |
|---------|-----------|----------------|
| Cross-platform sync | ❌ Manual | ✅ Automatic (uv.lock) |
| Custom CUDA version | ⚠️ Reinstall | ✅ Config file |
| Upstream updates | ❌ Manual merge | ✅ Auto-sync |
| Git-safe environment | ⚠️ Must exclude | ✅ Parent level |
| Reproducibility | ❌ Version ranges | ✅ Locked hashes |
| Maintenance | ❌ 2x bash+bat | ✅ 1x Python |

## Commands

### Unified CLI

```bash
comfy run [mode] [args]      # Run ComfyUI
comfy update                 # Update ComfyUI + sync
comfy backup                 # Backup environment
comfy restore [backup]       # Restore environment
comfy sync                   # Regenerate wrapper + lock + sync (all automated!)
comfy help                   # Show help
```

### Run ComfyUI

```bash
./comfy.sh run [mode] [args]
```

Attention modes:
- `sage` - SageAttention (default, fastest)
- `flash` - FlashAttention
- `pytorch` - PyTorch default
- `split` - Split cross-attention
- `quad` - Quad cross-attention
- `none` - No attention flags

### Update ComfyUI

```bash
./comfy.sh update
```

Workflow:
1. Backup current environment
2. Git pull latest ComfyUI
3. Sync wrapper from updated requirements.txt
4. Update and sync dependencies

### Manage Environment

```bash
# Backup
./comfy.sh backup

# Restore from latest
./comfy.sh restore

# Restore from specific backup
./comfy.sh restore uv.lock.backup_20260125_123000
```

### Sync Wrapper

After editing [wrapper_config.toml](wrapper_config.toml):

```bash
./comfy.sh sync              # Does everything: regenerate + lock + sync!
```

No manual chaining needed - fully automated.

## Customization Examples

### Change PyTorch CUDA Version

Edit [wrapper_config.toml](wrapper_config.toml):
```toml
[pytorch]
index_name = "pytorch-cu121"
index_url = "https://download.pytorch.org/whl/cu121"
```

```bash
./comfy.sh sync              # Automated: regenerate + lock + sync
```

### Add Custom Node Dependency

Edit [wrapper_config.toml](wrapper_config.toml):
```toml
[dependencies]
custom = [
    # ... existing packages
    "new-package>=1.0.0",
]
```

```bash
./comfy.sh sync
```

### Remove Custom Node Dependency

Just delete the line from [wrapper_config.toml](wrapper_config.toml) and run:
```bash
./comfy.sh sync
```

## Windows Setup

1. Install uv:
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. Sync environment (if coming from Linux):
   ```cmd
   cd D:\Apps\ComfyUI_portable
   sync_windows.bat
   ```

3. Run:
   ```cmd
   comfy.bat run sage
   ```

## Troubleshooting

### Environment mismatch
```bash
./restore_env.sh
```

### Check PyTorch version
```bash
.venv/bin/python -c "import torch; print(torch.__version__)"
```

### Force clean environment
```bash
rm -rf .venv
./comfy.sh sync
```

### Custom node dependency issues
See [CUSTOM_NODES.md](CUSTOM_NODES.md) for detailed guide on managing custom nodes with ComfyUI-Manager.

### Build decord2 from source on Windows (optional, for video features)

**Prerequisites:**
- Visual Studio 2017+ (Community edition is free)
- CMake 3.8+ (`choco install cmake`)
- FFmpeg (`choco install ffmpeg`)
- Git (`choco install git`)

**Automated build:**
```cmd
scripts\build_decord_windows.bat
```

This will:
1. Clone johnnynunez/decord2
2. Configure CMake for Windows
3. Open Visual Studio solution
4. Guide you through manual build steps

**Manual build (alternative):**
```cmd
cd temp
git clone --recursive https://github.com/johnnynunez/decord2
cd decord2\build
cmake -DCMAKE_CXX_FLAGS="/DDECORD_EXPORTS" -DCMAKE_CONFIGURATION_TYPES="Release" -G "Visual Studio 15 2017 Win64" ..
REM Open decord.sln, set Release, build
cd ..\python
python setup.py install --user
```

**Test installation:**
```cmd
python -c "from decord import VideoReader; print('✓ decord2 installed!')"
```

> **Note**: decord2 has no pre-built Windows wheels on PyPI or GitHub. Building from source is the only option for Windows video features in ComfyUI-RMBG SAM3 nodes.

## Migration Notes

If migrating from old setup with environment inside `ComfyUI/.venv`:

1. The old structure had environment deleted on `git reset`
2. New structure keeps environment at parent level (git-safe)
3. Old backups: Look for `.venv_backup/` if you need to recover anything
4. All shell/batch scripts now 3-line wrappers to Python scripts

## Development

All management logic is in `scripts/*.py`:
- Cross-platform Python code
- Easy to debug and test
- Shared utilities in `common.py`
- Shell/batch scripts are just thin wrappers

To add a new command:
1. Create `scripts/new_command.py`
2. Add wrapper `new_command.sh` / `new_command.bat`
3. Done!

## Files Reference

### User Interface
- **comfy.sh / comfy.bat** - Unified CLI (main interface)
- [wrapper_config.toml](wrapper_config.toml) - All customizations
- sync_windows.bat - Windows initial setup only

### Auto-Generated (Don't Edit)
- [pyproject.toml](pyproject.toml) - Generated from config + upstream
- `uv.lock` - Locked dependencies

### Backups
- `uv.lock.backup_*` - Environment snapshots
- `env_backup_*.txt` - Package lists

### Implementation
- `scripts/cli.py` - Unified CLI dispatcher
- `scripts/*.py` - All management logic (cross-platform)
