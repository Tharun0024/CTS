# Prior Authorization Policy Retrieval RAG System & Clinical Decision Agent

A comprehensive, high-performance, and clinically-grounded semantic search retrieval system and clinical decision engine for Prior Authorization (PA) medical policies, with a closed-loop provider-side recovery layer (Agent 2) integrated into the real Version-1 pipeline.

---

## 1. Project Architecture

The codebase separates concerns across adapters, RAG-specific schemas, semantic search/retrieval internals, the deterministic clinical decision agent (Agent 1), the provider-side recovery layer (Agent 2), and end-to-end orchestration services:

```text
cts/
├── adapters/            # Translation/adaptation layers
│   ├── rag_adapter.py     # Maps ClaimInput and legacy Policy criteria formatting
│   └── runtime_adapter.py # Normalizes Version-1 runtime data to CanonicalClaim;
│                          # get_provider_evidence_pool reads ONLY the provider DB
├── agent2/              # Agent 2: provider-side recovery & resubmission layer
│   ├── audit/             # AuditLogger: SQLite-persisted state transitions
│   ├── config.py          # NVIDIA settings + MAX_RESUBMISSION_ATTEMPTS (3)
│   ├── database/          # Provider DB access (repositories, importer)
│   ├── payer/             # Agent1Client boundary (payer responses in only)
│   ├── reasoning/         # RejectionAnalyzer (search concepts), CriterionMapper
│   ├── retrieval/         # Provider-side evidence retrieval & ranking
│   ├── schemas/           # Pydantic contracts (Evidence, PayerResponse, ...)
│   ├── submission/        # BoundaryFilter, PackageBuilder, VersionManager
│   ├── validators/        # Claim/evidence/LLM-output/submission validators
│   └── workflow/          # PriorAuthOrchestrator state machine
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
│   └── integrated_pipeline.py # Agent 1 pipeline + Agent 2 versioned recovery loop
├── tests/               # Pytest verification suites (incl. Agent 2 e2e scenarios A–K)
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

## 3. Agent 2: Provider-Side Recovery in the Real V1 Pipeline

Agent 2 is integrated through `services/integrated_pipeline.py` (`run_agent2_v1_pipeline` / `run_agent2_pipeline_from_db`). Every claim version — V1, V2, V3 — is re-decided by the **same** Agent 1 + RAG path; Agent 2 never makes coverage decisions and never duplicates Agent 1.

```text
CanonicalClaim -> RAG -> Agent 1 -> DecisionResponse -> routing
   -> (recoverable?) Agent 2 provider-evidence recovery -> release gate
   -> SubmissionPackage (new_evidence_delta) -> Agent 1 again -> final outcome
```

### V1 Routing Contract

| Agent 1 outcome / claim condition | Route | Agent 2 |
|---|---|---|
| `APPROVE` | Terminal | not invoked |
| `REJECT` with coverage exclusion | Hard terminal `REJECT` | not invoked |
| Lapsed eligibility (`eligibility_eligible=False`, coverage INACTIVE/LAPSED/TERMINATED/EXPIRED) | Terminal administrative `REJECT` | not invoked |
| Filing deadline exceeded (`filing_deadline_exceeded=True` / status EXCEEDED) | Terminal administrative `REJECT` | not invoked |
| Recoverable `REJECT` / `REQUEST_MORE_INFORMATION` (documentation, coding, medical necessity) | Recovery loop | invoked |
| `HUMAN_REVIEW` | Terminal | no direct recovery |

### Evidence Safety Guarantees

* **FOUND ≠ SATISFIED**: recovered provider evidence is only *found*; satisfaction is decided exclusively by Agent 1 re-evaluation of the new claim version.
* **Anti-fabrication provenance guard**: only records physically present in the provider evidence pool (by `evidence_id`) may enter a resubmission; nothing is ever invented.
* **Sensitivity release gate**: only `ROUTINE` evidence is released programmatically; `PROTECTED_*` and `UNKNOWN` sensitivity block the release and escalate to `HUMAN_REVIEW`.
* **Minimum necessary**: recovery selects only evidence matching Agent 1's requested keys / requested concepts.
* **Immutable versions**: claim snapshots are append-only (V1 → V2 → V3); each resubmission carries `new_evidence_delta` with only the newly added evidence IDs; history is never overwritten.
* **Bounded loop**: recovery is capped by `MAX_RESUBMISSION_ATTEMPTS` (default 3, `agent2/config.py`); when reached the pipeline stops safely and escalates to `HUMAN_REVIEW`.

### Trust Boundaries

* Agent 1 and the RAG pipeline never access the Big Patient Record (provider DB).
* Agent 2 never accesses payer-side data; it reads the provider evidence pool only (`adapters/runtime_adapter.py::get_provider_evidence_pool`) and consumes payer responses through the `PayerResponse` contract.

---

## 4. RAG vs LLM Responsibilities

### Policy Retrieval & Analysis (Deterministic)
The policy intelligence layer is performed before LLM generation by the local RAG pipeline:
1. Exact code matching, BM25, and FAISS vector retrieval.
2. Candidate pool reranking (BGEReranker) and single-policy consistency aggregation.
3. Deterministic clinical criteria analysis and Evidence Object construction.

### NVIDIA LLM Scope (Structured Formatting & Interpretation Only)
The generation/extraction layer uses NVIDIA Llama 3.1 8B Instruct through NVIDIA's OpenAI-compatible API.
* **Scope:** converting grounded Evidence Objects and records into structured JSON matching the target schemas, and (in Agent 2) interpreting payer rejection text into search concepts via `RejectionAnalyzer`.
* **Grounding:** the LLM never executes policy selection, clinical eligibility decisions, or exclusion evaluation — the coverage decision is always deterministic. Malformed or decision-leaking LLM output fails closed to `HUMAN_REVIEW`.

---

## 5. Installation & Setup

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
   Configure your NVIDIA settings in `.env` (used only for structured formatting / rejection interpretation — never for the coverage decision):
   ```env
   NVIDIA_API_KEY=your_nvidia_api_key_here
   NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
   NVIDIA_MODEL=meta/llama-3.1-8b-instruct
   ```
   The system remains runnable without an API key (deterministic fallback paths).

---

## 6. Execution Guide

Run all steps directly using the Python environment:

### 1. Build Search Indexes
Builds normalizations, chunks policies, generates embeddings, and constructs the FAISS and BM25 search indexes:
```bash
python -m scripts.build_index
```

### 2. Run Test Suite
Runs the comprehensive Pytest verification suites (main suite plus Agent 2 routing tests — 178 tests):
```bash
python -m pytest tests agent2/tests/test_orchestrator_routing.py -v
```
End-to-end Agent 2 scenarios (A–K: approve, recovery-to-approve, recoverable reject, unfound evidence, conflicting recovery, exclusion terminal, lapsed eligibility, filing deadline, human review, sensitive block, attempt cap) live in `tests/test_agent2_v1_end_to_end.py`.

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

## 7. Security

* API keys must be stored in environment variables (configured via `.env`).
* API keys must never be hardcoded or committed to version control.
* `.cache/`, `.venv/`, `.env/`, and generated `vector_store/` caches are excluded from version control.
* Administrative denials (lapsed eligibility, filing deadline) and coverage exclusions are enforced deterministically by programmatic gates — never by the LLM.
