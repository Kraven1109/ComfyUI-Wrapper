# ComfyUI Portable Workspace

Modern, maintainable ComfyUI workspace with unified Python scripts and cross-platform support.

## Quick Start

```bash
# Linux/Mac
./comfy.sh run sage         # Run with SageAttention
./comfy.sh update           # Update ComfyUI + dependencies
./comfy.sh backup           # Backup environment
./comfy.sh sync             # Regenerate wrapper (auto locks & syncs)
./comfy.sh help             # Show all commands

# Windows
comfy.bat run sage          REM Run with SageAttention
comfy.bat update            REM Update ComfyUI + dependencies
comfy.bat backup            REM Backup environment
comfy.bat sync              REM Regenerate wrapper (auto locks & syncs)
comfy.bat help              REM Show all commands
```

## Configuration

**Edit [wrapper_config.toml](wrapper_config.toml) for all customizations:**

```toml
# Change PyTorch CUDA version
[pytorch]
index_name = "pytorch-cu130"  # cu121, cu124, etc.
index_url = "https://download.pytorch.org/whl/cu130"

# Add/remove custom node dependencies
[dependencies]
custom = [
    "comfyui-manager>=4.0.5",
    "opencv-python",
    # ... add your packages here
]
```

After editing config:
```bash
./comfy.sh sync              # Automatically locks and syncs!
```

No need to chain commands - `comfy sync` does everything.

## Architecture

```
ComfyUI_portable/
├── comfy.sh / comfy.bat      # Unified CLI (main interface)
├── wrapper_config.toml       # ← Edit this for all customizations
├── pyproject.toml            # Auto-generated wrapper
├── uv.lock                   # Locked dependencies
├── .venv/                    # Virtual environment (not in git)
│
├── scripts/                  # Python implementation (cross-platform)
│   ├── cli.py                # Unified CLI dispatcher
│   ├── common.py             # Shared utilities
│   ├── run_comfy.py          # Run ComfyUI
│   ├── update_comfy.py       # Update workflow
│   ├── backup_env.py         # Backup environment
│   ├── restore_env.py        # Restore environment
│   └── sync_wrapper.py       # Sync pyproject.toml (automated)
│
└── ComfyUI/                  # Git repository (clean, auto-updated)
    ├── pyproject.toml        # Upstream metadata
    └── requirements.txt      # Upstream dependencies
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
