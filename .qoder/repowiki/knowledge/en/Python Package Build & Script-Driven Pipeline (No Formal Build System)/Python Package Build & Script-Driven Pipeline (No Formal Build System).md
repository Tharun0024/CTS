---
kind: build_system
name: Python Package Build & Script-Driven Pipeline (No Formal Build System)
category: build_system
scope:
    - '**'
source_files:
    - requirements.txt
    - config/config.yaml
    - scripts/build_index.py
    - .env.example
    - README.md
---

## What system/approach is used

This repository does **not** use a formal build system. There are no `Makefile`, `Dockerfile`, `pyproject.toml`, `setup.py`/`setup.cfg`, `tox.ini`, `noxfile.py`, or CI pipeline files in the repository. The project is a Python application distributed as source code with a flat `requirements.txt` dependency manifest and executed via direct `python` invocations of entry-point scripts.

The closest thing to a "build" is an **index-build script** (`scripts/build_index.py`) that orchestrates a multi-step RAG index construction pipeline: normalize policies, chunk them, generate BGE embeddings, persist `.npy` embeddings, build a FAISS vector index, and build a BM25 index — all driven by `config/config.yaml` paths and model names.

Runtime execution is done through:
- Standalone CLI scripts under `scripts/` (`build_index.py`, `benchmark.py`, `evaluate.py`, `check_data_quality.py`, `inspect_dataset.py`, `query_pipeline.py`, `verify_real_v1_runtime.py`, `verify_v1_final.py`).
- A FastAPI server launched via `uvicorn` from `api/main.py`.
- Pytest for tests (`pytest -v` per the README).

## Key files and packages

- `requirements.txt` — single-source dependency list pinned with minimum versions (`fastapi>=0.118.0`, `torch>=2.8.0`, `transformers>=4.57.0`, `sentence-transformers>=5.7.0`, `faiss-cpu>=1.15.0`, `rank-bm25>=0.2.2`, `pytest>=9.1.1`, etc.).
- `config/config.yaml` — central configuration for embedding/reranker models, device, candidate pool size, and file paths (models, embeddings, vector store, cache, raw/normalized/processed data locations).
- `scripts/build_index.py` — the canonical index-building pipeline; reads `config/config.yaml`, calls `normalize_policies_dataset`, `chunk_policies`, `BGEEmbedder.embed_texts`, `FAISSRetriever.build_index`, and `BM25Retriever.build_index`, and persists artifacts under `data/embeddings/` and `data/vector_store/`.
- `.env.example` — documents required environment variables for LLM providers (NVIDIA API key/model/url, OpenRouter key/model/url, OpenAI-compatible LLM endpoint), HuggingFace/Transformers/Torch cache directories, and a `DEBUG` flag.
- `README.md` — documents running tests via `python -m pytest -v`.

## Architecture and conventions

- **Flat Python package layout**: top-level modules (`rag/`, `decision/`, `agent2/`, `adapters/`, `services/`, `api/`, `transformation/`, `models/`) are imported directly; there is no packaging metadata, so installation is expected to be either `pip install -r requirements.txt` from the repo root or running scripts directly with the repo on `PYTHONPATH`.
- **Configuration-as-code**: all runtime tuning (model names, device, path prefixes) lives in `config/config.yaml`; scripts load it via `yaml.safe_load` rather than using argparse or env-driven config.
- **Artifact-driven pipeline**: the RAG pipeline produces persistent artifacts (`data/embeddings/chunk_embeddings.npy`, `data/vector_store/index.faiss`, `data/vector_store/bm25.pkl`, `data/normalized/normalized_policies.json`, `data/processed/chunks.json`) which downstream retrieval code consumes without recomputation.
- **Environment-driven secrets**: LLM provider credentials and cache roots are loaded via `python-dotenv` (`.env` / `.env.example`); no secrets are committed.
- **Testing**: pytest discovers tests under `tests/` and `agent2/tests/` automatically; no `pytest.ini` or `pyproject.toml` overrides exist, so default discovery rules apply.

## Conventions and constraints

- **No containerization**: no `Dockerfile` or docker-compose exists; deployment would require creating one externally.
- **No CI/CD**: no `.github/workflows/`, no GitHub Actions, GitLab CI, Jenkins, or similar pipeline definitions are present.
- **No packaging distribution**: no `pyproject.toml`, `setup.py`, or `MANIFEST.in`; the repo is intended to be consumed as a directory, not installed as a pip package.
- **Dependency pinning style**: `requirements.txt` uses `>=` lower bounds only (e.g. `torch>=2.8.0`), not exact pins — reproducibility relies on the virtual environment (`.venv/`) checked into the repo.
- **Model caching**: HF/Transformers/Torch caches are externalized via `HF_HOME`, `TRANSFORMERS_CACHE`, `HF_DATASETS_CACHE`, `TORCH_HOME` environment variables documented in `.env.example`; the default local `.cache/hf` path in `config.yaml` is overridden by these env vars at runtime.
- **Index rebuild contract**: `scripts/build_index.py` is the single entry point that must be re-run whenever the raw policy corpus changes; it writes deterministic outputs to the paths declared in `config/config.yaml`.