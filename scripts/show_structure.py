"""
ComfyUI Workspace Architecture Visualization

Run: python scripts/show_structure.py
"""

from pathlib import Path


def show_structure():
    """Display workspace structure with annotations."""
    
    structure = """
╔═══════════════════════════════════════════════════════════════════════
║  ComfyUI Portable Workspace - Unified CLI
╚═══════════════════════════════════════════════════════════════════════

📁 ComfyUI_portable/
│
├─ 🎯 UNIFIED CLI (Use these!)
│  ├─ comfy.sh                      Linux/Mac: ./comfy.sh <command>
│  └─ comfy.bat                     Windows:   comfy.bat <command>
│
│     Commands:
│       comfy run [mode] [args]    - Launch ComfyUI
│       comfy update               - Update everything
│       comfy backup               - Create backup
│       comfy restore [backup]     - Restore environment
│       comfy sync                 - Regenerate + lock + sync (automated!)
│       comfy help                 - Show help
│
├─ 📝 wrapper_config.toml         ← EDIT THIS for customizations
│  ├─ [pytorch]                     (CUDA version, index URL)
│  └─ [dependencies]                (custom packages)
│
├─ 📄 pyproject.toml              ← AUTO-GENERATED (don't edit)
├─ 🔒 uv.lock                     ← Locked dependencies
├─ 📦 .venv/                      ← Virtual environment (git-safe)
│
├─ 🐍 scripts/                    ← ALL LOGIC HERE (cross-platform)
│  ├─ cli.py                        (unified CLI dispatcher)
│  ├─ common.py                     (shared utilities, path helpers)
│  ├─ run_comfy.py                  (launch ComfyUI with attention modes)
│  ├─ update_comfy.py               (git pull + sync workflow)
│  ├─ backup_env.py                 (snapshot environment)
│  ├─ restore_env.py                (restore from backup)
│  ├─ sync_wrapper.py               (generate + lock + sync - automated!)
│  └─ show_structure.py             (this file)
│
├─ 🪟 sync_windows.bat            ← Windows initial setup only
│
├─ 💾 Backups
│  ├─ uv.lock.backup_YYYYMMDD_*     (lock snapshots)
│  └─ env_backup_YYYYMMDD_*.txt     (package lists)
│
├─ 📚 Documentation
│  ├─ README.md                     (main docs)
│  ├─ README_WORKSPACE.md           (legacy notes)
│  └─ REFACTORING.md                (change summary)
│
└─ 📂 ComfyUI/                    ← Git repo (clean, auto-updated)
   ├─ pyproject.toml                (upstream metadata - SOURCE)
   ├─ requirements.txt              (upstream deps - SOURCE)
   └─ main.py                       (entry point)

═══════════════════════════════════════════════════════════════════════
WORKFLOW: How Updates Work (Fully Automated!)
═══════════════════════════════════════════════════════════════════════

1. Edit wrapper_config.toml
2. Run: ./comfy.sh sync
   ├─ sync_wrapper.py        (read config + upstream, generate pyproject.toml)
   ├─ uv lock                (update lock with new deps)
   └─ uv sync                (install to .venv)
   
   All automatic - no manual chaining!

═══════════════════════════════════════════════════════════════════════
KEY FEATURES
═══════════════════════════════════════════════════════════════════════

✅ Unified CLI              comfy.sh / comfy.bat (one command for all)
✅ Automated workflows       comfy sync does regenerate + lock + sync
✅ Single config file        wrapper_config.toml (not 3+ files)
✅ Cross-platform            Python scripts (not bash + batch)
✅ No duplication            350 lines (not 1000)
✅ Git-safe                  .venv at parent (not in ComfyUI/)
✅ Reproducible              uv.lock with hashes
✅ Auto-sync                 From upstream requirements.txt

═══════════════════════════════════════════════════════════════════════
QUICK COMMANDS (The Smart Way!)
═══════════════════════════════════════════════════════════════════════

Linux/Mac:
  ./comfy.sh run sage              Launch ComfyUI with SageAttention
  ./comfy.sh run flash             Launch with FlashAttention
  ./comfy.sh update                Update everything (backup + git + sync)
  ./comfy.sh backup                Create backup snapshot
  ./comfy.sh restore               Restore from latest backup
  ./comfy.sh sync                  Regenerate + lock + sync (automated!)
  ./comfy.sh help                  Show all commands

Windows:
  comfy.bat run sage               Launch ComfyUI
  comfy.bat update                 Update everything
  comfy.bat sync                   Regenerate + lock + sync

Customize:
  1. Edit wrapper_config.toml
  2. Run: ./comfy.sh sync          ← This is ALL you need!

═══════════════════════════════════════════════════════════════════════
"""
    
    print(structure)


if __name__ == "__main__":
    show_structure()
