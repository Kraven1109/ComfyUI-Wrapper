# Copilot instructions — ComfyUI workspace 🔧

Purpose: provide short, actionable context so an AI coding agent can be immediately productive working on this repository.

---

## 1) Big picture (what to read first) 📚
- This workspace wraps the upstream ComfyUI app so it is portable and reproducible. See: `README.md` (root) and `ComfyUI/README.md` for authoritative architecture and run instructions.
- Key components:
  - `scripts/` — wrapper tooling (cross-platform CLI): `cli.py`, `run_comfy.py`, `sync_wrapper.py`.
  - `wrapper_config.toml` — central configuration (CUDA version, custom deps). After edits run `./comfy.sh sync` (or `comfy.bat sync`).
  - `ComfyUI/` — the app code: `main.py` (entry point), `server.py`, `app/` (backend), `comfy/` (core model logic), `custom_nodes/` and `user/` (extensions & workflows).
  - `uv.lock` / `pyproject.toml` — pinned dependencies; do not hand-edit `pyproject.toml` unless you understand the sync pipeline.

## 2) Typical developer workflows (how to run / test / debug) 🛠️
- Run locally (portable workspace): use top-level wrappers:
  - Linux/Mac: `./comfy.sh run [mode]` (modes: `sage`, `flash`, `pytorch`, `split`, `quad`, `none`)
  - Windows: `comfy.bat run sage`
  - Direct run: `python ComfyUI/main.py [--enable-manager]` for dev debugging.
- Sync/update environment: `./comfy.sh sync` (regenerates `pyproject.toml`, updates `uv.lock`, installs deps).
- Tests:
  - Unit tests: `pip install -r ComfyUI/tests-unit/requirements.txt` then `pytest tests-unit/` from `ComfyUI/`.
  - Integration/long-running test harnesses live in `ComfyUI/tests/` (read test docstrings and fixtures).
- Debugging tips:
  - Reproduce with a small configuration or a single workflow frame first (see workflow-specific guide in `ComfyUI/user/default/workflows/.github/`).
  - For server endpoints, run with `--listen` and `--port` flags and use the tests in `ComfyUI/tests-unit/` as examples. Many tests are asyncio-based (pytest-asyncio).

## 3) Project-specific conventions & patterns ⚙️
- Workflows are JSON DAGs (fields: `nodes`, `links`, `groups`, `config`, `extra`, `last_node_id`, `last_link_id`, `version`). See `ComfyUI/user/default/workflows/.github/copilot-instructions.md` for details and examples.
- Custom nodes live under `ComfyUI/custom_nodes/` and may include their own `.github/copilot-instructions.md` for module-specific guidance — prefer reading those first when modifying nodes.
- Models & assets: put checkpoints in `ComfyUI/models/checkpoints`, VAE in `ComfyUI/models/vae`, embeddings in `ComfyUI/models/embeddings`.
- Manager extension: `ComfyUI-Manager` is integrated; enable with `--enable-manager` and read `ComfyUI/manager_requirements.txt`.
- Performance patterns: code includes many opt-in optimizations (TeaCache, MagCache, SageAttention, GGUF quantization). Changes to sampling/optimizations often require validation via end-to-end flows (small sample → full run).

## 4) Integration points & external deps 🔗
- Heavy ML deps: PyTorch (CUDA variants), Hugging Face format models, optional ROCm/XPU/Ascend support. Check `wrapper_config.toml` for PyTorch index settings.
- Frontend lives in `ComfyUI/web/` and `web_custom_versions/` (served by the Python server). Frontend changes may require build steps and browser reloads.
- ComfyUI exposes an HTTP API and background services (see `ComfyUI/api_server/` and `ComfyUI/app/`). Many internal tests target these interfaces.

## 5) Where to find more focused guidance 🔍
- Workflow/Video-specific: `ComfyUI/user/default/workflows/.github/copilot-instructions.md` (extensive, includes node-level parameter guidance and VRAM tips).
- Custom node or component-specific copilot guides (examples):
  - `ComfyUI/custom_nodes/ComfyUI-Llama/.github/copilot-instructions.md`
  - `ComfyUI/custom_nodes/comfyUI-TTSS/.github/copilot-instruction.md`
- Tests + test runner: `ComfyUI/tests-unit/README.md` and test files under `ComfyUI/tests-unit/`.

## 6) Typical tasks an AI agent can do first ✅
- Triage failing tests: run `pytest` (see failing trace), locate test and relevant module under `ComfyUI/`, propose minimal fix + test.
- Small feature work: add a CLI flag in `scripts/cli.py` and wire up wrapper scripts / update `README.md` with examples.
- Improve node docs: add short examples next to node definitions in `ComfyUI/` (search `nodes.py` and `custom_nodes/*/README.md`).
- Performance regression checks: add a small reproducible benchmark (single frame, deterministic seed) and add tests under `ComfyUI/tests/`.

---

If this summary is useful I can (1) incorporate any existing top-level `.github` guidance into this file, or (2) extract quick-start snippets into `CONTRIBUTING.md` / `docs/` for humans. Please tell me which you prefer or which area to expand. 🙌
