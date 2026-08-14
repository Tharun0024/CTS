# Generalized Prior Authorization Policy Retrieval RAG System

A high-performance, clinically-grounded semantic search and criteria extraction engine for Prior Authorization (PA) medical policies.

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
   Modify `.env` to configure your API keys or leave `LLM_API_KEY=mock_api_key_for_testing` to run in safe offline mock/deterministic mode.

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
