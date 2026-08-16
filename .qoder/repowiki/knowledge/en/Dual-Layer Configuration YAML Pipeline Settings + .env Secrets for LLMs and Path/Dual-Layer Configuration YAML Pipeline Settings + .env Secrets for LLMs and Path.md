---
kind: configuration_system
name: 'Dual-Layer Configuration: YAML Pipeline Settings + .env Secrets for LLMs and Paths'
category: configuration_system
scope:
    - '**'
source_files:
    - config/config.yaml
    - .env.example
    - agent2/config.py
    - api/main.py
    - rag/llm/llm_client.py
    - agent2/reasoning/criterion_mapper.py
    - agent2/reasoning/rejection_analyzer.py
    - scripts/benchmark.py
    - scripts/build_index.py
---

## What system/approach is used

The repository uses a **two-layer configuration approach** with no centralized config loader framework:

1. **Static pipeline settings** are loaded from `config/config.yaml` via PyYAML (`yaml.safe_load`) at application startup.
2. **Runtime secrets and environment toggles** (API keys, model names, URLs, debug flags) are read directly from environment variables using `os.getenv`, with `.env` files loaded by `python-dotenv` in the Agent 2 subsystem.

There is no single typed configuration object; instead, each module reads what it needs from either the global `CONFIG` dict (RAG API) or bare `os.getenv` calls scattered across modules.

## Key files and packages

- `config/config.yaml` — Central YAML file holding RAG pipeline tuning parameters: embedding/reranker model names, candidate pool size, final chunk count, device selection, and all filesystem paths (models, embeddings, vector store, cache, raw/normalized/processed data).
- `.env.example` — Template of required environment variables: NVIDIA OpenAI-compatible LLM keys/URLs/model, OpenRouter key/URL/model, HuggingFace/Transformers/Torch cache directories, and a `DEBUG` flag.
- `agent2/config.py` — Loads `.env` via `load_dotenv()`, defines project-relative base dirs (`PROJECT_ROOT`, `WORKSPACE_DIR`, `DB_PATH`, `FHIR_DIR`, `POLICIES_DIR`, `CMS_JSONL_PATH`), and exposes `MAX_RESUBMISSION_ATTEMPTS`, `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_MODEL`, `GEMINI_API_KEY` as module-level constants.
- `api/main.py` — FastAPI lifespan loads `config/config.yaml` into a process-global `CONFIG` dict, then instantiates embedder, FAISS/BM25 retrievers, reranker, policy aggregator, evidence builder, LLM client, prompt builder, output validator, and query builder using values from that dict.
- `rag/llm/llm_client.py` — Reads `NVIDIA_API_KEY` / `LLM_API_KEY`, `NVIDIA_API_URL` / `LLM_API_URL`, `NVIDIA_MODEL` / `LLM_MODEL`, and `DEBUG` via `os.getenv` to configure the LLM client used by the RAG pipeline.
- `agent2/reasoning/criterion_mapper.py`, `agent2/reasoning/rejection_analyzer.py` — Duplicate the same `os.getenv` pattern for NVIDIA/OpenRouter credentials inside Agent 2 reasoning components.
- `scripts/benchmark.py`, `scripts/build_index.py`, `scripts/check_data_quality.py` — Load `config/config.yaml` directly to resolve model names, device, and data paths for offline scripts.

## Architecture and conventions

- **Separation of concerns**: `config.yaml` holds *pipeline behavior* (which models, how many candidates, where data lives); `.env` holds *runtime secrets* (API keys, URLs, model identifiers). The two are never mixed.
- **Path resolution**: All file paths in `config.yaml` are relative to the project root. Scripts and the API resolve them with `os.path.join("config", "config.yaml")` or similar relative joins. Agent 2 computes absolute paths via `os.path.dirname(os.path.abspath(__file__))` to derive `PROJECT_ROOT`, then builds workspace/db/FHIR/policies paths under it.
- **Global state caching**: The FastAPI app caches the parsed `CONFIG` dict and all heavy components (embedders, retrievers, indexes) as module-level globals initialized once in the `lifespan` context manager, so config is only read once per process.
- **Fallback chains for env vars**: When reading LLM settings, code falls back through multiple variable names (e.g. `NVIDIA_API_URL` → `LLM_API_URL` → default URL; `NVIDIA_BASE_URL` → `NVIDIA_API_URL` → default URL) so both old and new naming schemes work.
- **Debug toggle**: A `DEBUG` environment variable (default `"false"`) gates verbose logging in both the API endpoints and the LLM client.

## Conventions and constraints

- **YAML-only static config**: There is exactly one YAML configuration file (`config/config.yaml`). No TOML, JSON config, or CLI flags override these values at runtime.
- **No validation schema**: `config.yaml` is loaded with `yaml.safe_load` and consumed as a plain dict; there is no pydantic or jsonschema validation of the YAML structure.
- **Required data files**: The API explicitly checks that `paths.processed_chunks` exists before starting and raises `FileNotFoundError` if missing — this is the only enforced constraint on config correctness.
- **Secrets must be in `.env`**: Agent 2 calls `load_dotenv()` at import time; other modules rely on the OS environment being pre-populated (e.g. via Docker, systemd, or manual export). There is no fallback to defaults for API keys — they default to empty strings, which will cause downstream failures if not set.
- **Model/device coupling**: `embedding_model`, `reranker_model`, and `device` in `config.yaml` are passed verbatim to sentence-transformers/HF AutoModel constructors; changing them requires compatible model artifacts to exist at the configured `paths.cache` directory.
- **Agent 2 workspace auto-creation**: `agent2/config.py` calls `os.makedirs(WORKSPACE_DIR, exist_ok=True)` to ensure the SQLite database location exists before any agent runs.