---
kind: dependency_management
name: Python Dependencies via Flat requirements.txt with Virtual Environment
category: dependency_management
scope:
    - '**'
source_files:
    - requirements.txt
    - .env.example
    - .gitignore
---

## What system/approach is used

The repository manages Python dependencies exclusively through a single flat `requirements.txt` file at the project root. There are no lockfiles (no `requirements.lock`, `Pipfile.lock`, `poetry.lock`, or `pyproject.toml`), no vendored third-party packages, and no private PyPI registry configuration. A local virtual environment directory `.venv/` exists but is empty in this snapshot, indicating it is created per machine rather than committed.

## Key files and packages

- `requirements.txt` — the sole manifest declaring all runtime and test dependencies with minimum-version pins (`>=`).
- `.env.example` — documents required runtime secrets and model cache locations; consumed by `python-dotenv` to load `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, `LLM_API_KEY`, plus Hugging Face / Torch cache paths.
- `.gitignore` — excludes `.venv/`, `.cache/`, `.pytest_cache/`, and other generated artifacts so the virtual environment stays local.
- `config/config.yaml` — application-level configuration loaded via `pyyaml`; not a dependency manifest.

## Architecture and conventions

- **Flat dependency list**: All 15 dependencies are declared in one file without grouping, sub-dependencies, or extras. The list covers the FastAPI server (`fastapi`, `uvicorn`), data/ML stack (`numpy`, `pandas`, `torch`, `transformers`, `sentence-transformers`, `faiss-cpu`, `rank-bm25`, `scikit-learn`), config/env loading (`pyyaml`, `python-dotenv`), testing (`pytest`), and HTTP client (`httpx`).
- **Minimum-version pins only**: Every entry uses `>=` constraints rather than exact versions, allowing pip to resolve the latest compatible version at install time. This means builds are reproducible only when run against the same resolver state.
- **No lockfile strategy**: There is no mechanism to pin transitive dependencies. The README instructs users to run `pip install -r requirements.txt` directly.
- **Virtual environment per developer**: `.venv/` is gitignored, so each developer creates their own isolated environment. No shared lock or pinned environment is distributed.
- **Runtime secrets via env vars**: Third-party service credentials (NVIDIA Inference API, OpenRouter, OpenAI-compatible LLM endpoint) are not bundled; they must be provided through an `.env` file following the shape of `.env.example`. Model download caches are redirected via `HF_HOME`, `TRANSFORMERS_CACHE`, `HF_DATASETS_CACHE`, and `TORCH_HOME` environment variables.

## Conventions and constraints

- **Single source of truth**: `requirements.txt` is the only declared dependency surface; adding a new library requires editing this file.
- **No private registries or authentication**: No `pip.conf`, `~/.netrc`, or index URLs are present, so all packages are resolved from the public PyPI index.
- **No vendoring**: No `vendor/`, `third_party/`, or inline copies of third-party code exist under version control.
- **Environment isolation enforced by gitignore**: `.venv/`, `.cache/`, `.pytest_cache/`, and similar directories are excluded from version control, keeping dependency resolution local to each developer's machine.
- **Test dependencies co-mingled**: `pytest` is listed alongside runtime dependencies rather than separated into a `dev-requirements.txt` or optional extra.