# Prior Authorization Policy Retrieval RAG System & Clinical Decision Agent

A comprehensive, high-performance, and clinically-grounded semantic search retrieval system and clinical decision engine for Prior Authorization (PA) medical policies.

---

## 1. Project Architecture

The codebase separates concerns across adapters, RAG-specific schemas, semantic search/retrieval internals, the deterministic clinical decision agent (Agent 1), and end-to-end orchestration services:

```text
Y:\CTS
├── adapters/            # Translation/adaptation layers
│   ├── rag_adapter.py     # Maps ClaimInput and legacy Policy criteria formatting
│   └── runtime_adapter.py # Normalizes Version-1 runtime data to CanonicalClaim
├── api/
│   └── main.py          # Thin FastAPI routes delegating orchestration to services
├── config/
│   └── config.yaml      # Embedding models, rerankers, device settings, and data paths
├── data/                # Vector store, raw data (ragdata.jsonl), processed chunks
├── DATA-VERSION1/       # Version-1 SQLite database source files (patient, payer data)
├── decision/            # Agent 1 deterministic clinical decision engine
│   ├── agent.py           # Main orchestrator agent wrapper class
│   ├── decision_logic.py  # Applies the decision hierarchy resolution
│   ├── evidence_evaluator.py # Verifies evidence confidence, ambiguity, and fact compliance
│   ├── llm_prompt.py      # LLM prompting and guidelines (including injection safety)
│   ├── llm_provider.py    # OpenAI-compatible API providers (OpenRouter, NVIDIA)
│   ├── llm_schemas.py     # Pydantic schemas for structured LLM parsing
│   ├── policy_evaluator.py # Dotted-path extraction and operator clinical criteria rules
│   └── schemas.py         # Base decision engine data structures
├── models/
│   └── rag_models.py    # RAG input/output schemas (ClaimInput, ClaimOutput, etc.)
├── rag/                 # RAG retrieval internals
│   ├── aggregation/       # Policy Consistency Gate (cross-policy contamination prevention)
│   ├── analyzer/          # Deterministic analysis
│   ├── chunking/          # Policy document chunking
│   ├── embeddings/        # SentenceTransformers embedder wraps (BGEEmbedder)
│   ├── evidence/          # Clinical evidence assembly
│   ├── llm/               # LLM interaction clients (formatting layer)
│   ├── normalization/     # Text/policy preprocessing normalizers
│   ├── query_builder/     # Multi-query expansion builder
│   ├── reranking/         # BGEReranker scoring and filtering
│   ├── retrieval/         # Multi-way retrieval (exact match, BM25 keyword, FAISS semantic)
│   └── validation/        # Output format checks and recovery formatters
├── reports/             # Generated reports (benchmarks, data quality, dataset profile)
├── scripts/             # Admin, indexing, and debugging utilities
├── services/            # Service orchestration layer
│   └── integrated_pipeline.py # Core integration loop orchestrator
├── tests/               # Pytest verification suites
└── transformation/
    └── canonical_claim.py # Stable domain-model contract (CanonicalClaim)
```

---

## 2. Key Features & Grounding Safeguards

1. **Three-Way Retrieval Pipeline**:
   * **Exact Lookup**: Matches claims on direct identifiers (Payer, Policy ID, Procedure Code, Diagnosis Codes).
   * **Semantic Search (BGE/FAISS)**: Captures semantic context and clinical meaning.
   * **Keyword Matching (BM25)**: Ensures exact terminology overlay (e.g., specific drug names, CPT codes).
2. **Policy Consistency Gate**:
   * Enforces a strict 0% cross-policy contamination rate. Picks the single best-matching policy and aggregates chunks from *only* that policy.
3. **Deterministic Clinical Decision Agent (Agent 1)**:
   * Evaluates patient clinical data against policy criteria, exclusions, and evidence quality rules.
   * Compiles decisions according to a deterministic hierarchy resulting in: `APPROVE`, `REJECT`, `REQUEST_MORE_INFORMATION`, or `HUMAN_REVIEW`.
4. **Safety & Grounding Safeguards**:
   * Strictly forbids decision-leaking keyword output from the LLM (e.g., `APPROVE`, `REJECT`, `DENY`, `MET`, `NOT_MET`).
   * Safety states, unresolved policy paths, or malformed JSON from the LLM fail-closed directly to `HUMAN_REVIEW` or `REQUEST_MORE_INFORMATION`.

---

## 3. RAG vs LLM Responsibilities

### Policy Retrieval & Analysis (Deterministic)
The policy intelligence layer is performed before LLM generation by the local RAG pipeline:
1. Exact code matching, BM25, and FAISS vector retrieval.
2. Candidate pool reranking (BGEReranker) and single-policy consistency aggregation.
3. Deterministic clinical criteria analysis and Evidence Object construction.

### NVIDIA LLM Scope (Structured Formatting)
The final generation/extraction layer uses NVIDIA Llama 3.1 8B Instruct through NVIDIA's OpenAI-compatible API.
* **Scope:** It is responsible **only** for converting the grounded Evidence Object and user records into structured JSON formats matching the target schemas.
* **Grounding:** The LLM does not execute policy selection, clinical eligibility decisions, or evaluate exclusions, preventing hallucinated outcomes.

---

## 4. Installation & Setup

1. **Requirements**:
   * Python 3.12+
   * Dependencies listed in `requirements.txt`

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment (`.env`)**:
   Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
   Configure your NVIDIA API key in `.env`:
   ```env
   NVIDIA_API_KEY=your_nvidia_api_key_here
   ```

---

## 5. Execution Guide

Run all steps directly using the Python environment:

### 1. Build Search Indexes
Builds normalizations, chunks policies, generates embeddings, and constructs the FAISS and BM25 search indexes:
```bash
python -m scripts.build_index
```

### 2. Run Test Suite
Runs the comprehensive Pytest verification test suite:
```bash
python -m pytest -v
```

### 3. Evaluate Pipeline
Runs evaluation queries against the retrieval engine and calculates Recall@K, MRR, and contamination metrics:
```bash
python -m scripts.evaluate
```

### 4. Run Benchmarks
Measures resource utilization, memory consumption, file footprint sizes, and component latencies (P50/P90/P99):
```bash
python -m scripts.benchmark
```

### 5. Start API Server
Launches the FastAPI Prior Authorization Triage web service:
```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

### 6. Run Integrated CLI Query Tool
Runs the integrated end-to-end pipeline CLI on a specific claim file:
```bash
python -m scripts.query_pipeline data/test_claim_aetna_knee.json
```

---

## 6. Security

* API keys must be stored in environment variables (configured via `.env`).
* API keys must never be hardcoded or committed to version control.
* `.cache/`, `.venv/`, `.env/`, and generated `vector_store/` caches are excluded from version control.
