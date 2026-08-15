# Generalized Prior Authorization Policy Retrieval RAG System

A high-performance, clinically-grounded semantic search and criteria extraction engine for Prior Authorization (PA) medical policies.

### LLM Provider Migration

The project previously used Gemini 2.5 Flash for the final generation stage.
Due to the higher latency we have changed to NVIDIA API
The current implementation uses NVIDIA Llama 3.1 8B Instruct through NVIDIA's hosted OpenAI-compatible API.

The retrieval and deterministic policy-analysis architecture remains unchanged.

Only the final LLM provider has been changed.

## Key Features

1. **Three-Way Retrieval Pipeline**:
   * **Exact Lookup**: Matches claims on direct identifiers (Payer, Policy ID, Procedure Code, Diagnosis Codes).
   * **Semantic Search (BGE/FAISS)**: Captures semantic context and clinical meaning.
   * **Keyword Matching (BM25)**: Ensures exact terminology overlay (e.g., specific drug names, CPT codes).
2. **Policy Consistency Gate**:
   * Enforces a strict 0% cross-policy contamination rate. Picks the single best-matching policy and aggregates chunks from *only* that policy.
3. **Deterministic Information Extraction**:
   * Extracts medical necessity criteria, diagnostic thresholds, exclusions, limitations, and documentation requirements without relying on downstream LLM decisions.
4. **Safety & Grounding Safeguards**:
   * Strictly forbids decision-leaking keyword output (e.g., `APPROVE`, `REJECT`, `DENY`, `MET`, `NOT_MET`).
   * Implements a deterministic fallback formatting engine if the LLM output is unavailable, invalid, or violates schema validation.
5. **FastAPI Service**:
   * Exposes a `/triage` POST endpoint for real-time claim evaluation.

---

## Current Architecture

```text
INPUT JSON
  |
  v
Schema Validation
  |
  v
Query Builder
  |
  +-------------------+-------------------+
  |                   |                   |
  v                   v                   v
Exact Code          BGE Embedding        BM25
Matching               |                  Search
             v
           FAISS
  |                   |                   |
  +-------------------+-------------------+
            |
            v
         Candidate Pool
           Top 10
            |
            v
        BGE Reranker V2 M3
            |
            v
          Top 1-3
         Policy Chunks
            |
            v
        Policy Aggregator
            |
            v
      Deterministic Analyzer
            |
        +---------+---------+
        |         |         |
        v         v         v
       Criteria  Documents Exclusions
        |         |         |
        +---------+---------+
            |
            v
        Evidence Object
            |
            v
       NVIDIA Llama 3.1 8B
            |
            v
        JSON Schema Check
            |
            v
           FINAL JSON
```

NVIDIA is used only after retrieval, reranking, policy aggregation, and deterministic analysis are complete. The LLM receives a grounded Evidence Object and performs final JSON generation.

---

## Installation & Setup

1. **Requirements**:
   * Python 3.10+
   * PyTorch (configured for CPU-only execution)
   * FAISS
   * Transformers & Sentence-Transformers

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment (`.env`)**:
   Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
  Configure the NVIDIA API key through an environment variable:
  ```env
  NVIDIA_API_KEY=your_nvidia_api_key_here
  ```
  Never commit real API keys to source control.

---

## NVIDIA LLM Configuration

The final generation layer uses NVIDIA Llama 3.1 8B Instruct through NVIDIA's OpenAI-compatible API.

Provider:
NVIDIA

Model:
meta/llama-3.1-8b-instruct

Base URL:
https://integrate.api.nvidia.com/v1

Environment variable:
NVIDIA_API_KEY

Example:
```env
NVIDIA_API_KEY=your_nvidia_api_key_here
```

IMPORTANT:
Never commit the real NVIDIA API key to source control.

---

## RAG vs LLM Responsibilities

### RAG and Deterministic Policy Intelligence

The policy intelligence layer is performed before LLM generation by:

1. Exact code matching
2. BGE embeddings
3. FAISS semantic retrieval
4. BM25 lexical retrieval
5. Candidate pool generation
6. BGE Reranker V2 M3
7. Policy aggregation
8. Deterministic policy analysis
9. Evidence Object generation

The policy dataset is the source of truth. The LLM receives the resulting grounded Evidence Object.

### NVIDIA LLM Scope (Final Formatting Only)

The NVIDIA LLM is responsible only for converting the validated Evidence Object into the required final JSON format.

The NVIDIA LLM is not responsible for:

- policy retrieval
- vector search
- FAISS search
- BM25 search
- reranking
- policy selection
- medical necessity decision
- approval
- rejection
- pend decision
- requesting more information

Grounding and safety constraints:

- The LLM must not invent policy criteria.
- The LLM must not invent documentation requirements.
- The LLM must not invent policy IDs.
- The LLM must not mix information from different policies.
- The LLM must not make approve/reject decisions.
- Final JSON is validated after LLM generation.

---

## Execution Guide

Use the master runner script `run.py` at the root directory to run all pipeline commands:

### 1. Build Indexes
Builds normalizations, chunks policies, generates embeddings, and constructs the FAISS and BM25 search indexes:
```bash
python run.py --build-index
```

### 2. Run Test Suite
Runs the comprehensive Pytest verification test suite:
```bash
python run.py --test
```

### 3. Evaluate Pipeline
Runs evaluation queries against the retrieval engine and calculates Recall@K, MRR, and contamination metrics:
```bash
python run.py --evaluate
```

### 4. Run Benchmarks
Measures resource utilization, memory consumption, file footprint sizes, and component latencies (P50/P90/P99):
```bash
python run.py --benchmark
```

### 5. Start API Server
Launches the FastAPI Prior Authorization Triage web service:
```bash
python run.py --serve
```

---

## API Schemas

### POST `/triage`
**Input Payload (`ClaimInput`):**
```json
{
  "claim_id": "CLM-100",
  "insurance": {
    "primary": {
      "payer": "CMS",
      "policy_id": "NCD-20.8.3"
    }
  },
  "diagnosis": [
    {
      "code": "I49.5",
      "description": "Sick sinus syndrome"
    }
  ],
  "procedure": {
    "code": "33206",
    "description": "Insertion of pacemaker"
  },
  "clinical_domain": "cardiology"
}
```

**Output Response (`ClaimOutput`):**
```json
{
  "claim_id": "CLM-100",
  "policy_matches": [
    {
      "policy_id": "NCD-20.8.3",
      "payer": "CMS (Medicare)",
      "relevance_score": 0.95
    }
  ],
  "criteria": [
    {
      "criterion_id": "C01",
      "criterion": "Single Chamber and Dual Chamber Permanent Cardiac Pacemakers — medical necessity / coverage criteria",
      "policy_requirement": "Covered for non-reversible symptomatic bradycardia caused by sinus node dysfunction and/or second- or third-degree atrioventricular (AV) block...",
      "source": {
        "policy_id": "NCD-20.8.3",
        "section": "Coverage Criteria"
      }
    }
  ],
  "documentation_requirements": []
}
```

The final output schema remains unchanged after migrating from Gemini to NVIDIA. The API input/output contract is unchanged.

Required response shape:

```json
{
  "claim_id": "...",
  "policy_matches": [...],
  "criteria": [...],
  "documentation_requirements": [...]
}
```

---

## Security

- API keys must be stored in environment variables.
- API keys must never be hardcoded.
- API keys must never be committed to Git.
- The real NVIDIA API key must never be included in README.md.
- `.env` should remain excluded from version control.

---

## Latency Notes

NVIDIA Llama 3.1 8B was selected as the current final-generation model to provide a lightweight, low-latency LLM layer for the existing RAG pipeline.

Latency should be measured separately for:

- retrieval
- reranking
- deterministic analysis
- LLM generation
- JSON validation
- total end-to-end processing

Latency benchmarks are environment-dependent and should be measured using the project's benchmark procedure.
