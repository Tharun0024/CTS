---
kind: error_handling
name: Fail-Closed Error Handling with Pydantic Validation, HTTPException Wrapping, and Audit-Logged State Transitions
category: error_handling
scope:
    - '**'
source_files:
    - api/main.py
    - services/integrated_pipeline.py
    - agent2/workflow/orchestrator.py
    - agent2/audit/audit_logger.py
    - decision/agent.py
    - decision/schemas.py
    - agent2/validators/claim_validator.py
    - adapters/rag_adapter.py
    - adapters/runtime_adapter.py
---

## System Overview

The codebase uses a **fail-closed** error-handling strategy centered on three layers: (1) strict input validation via Pydantic models, (2) explicit `ValueError`/`FileNotFoundError` raises for contract violations inside business logic, and (3) top-level exception wrapping that converts unhandled errors into structured responses — either FastAPI `HTTPException`s at the API boundary or `DecisionResponse` objects with `outcome=HUMAN_REVIEW` in the decision pipeline. There is no custom exception hierarchy; all domain-specific failures are expressed as plain Python exceptions or as structured result objects.

## Key Files and Packages

- **API boundary (`api/main.py`)**: The only place where external-facing errors are surfaced. Each endpoint wraps its body in `try/except ValidationError` → `HTTPException(422)` and a catch-all `except Exception` → `HTTPException(500)`. Startup `lifespan` raises `FileNotFoundError` when required RAG artifacts are missing.
- **Integrated pipeline (`services/integrated_pipeline.py`)**: The central fail-closed hub. Every stage of the RAG + Agent 1 flow is wrapped in `try/except Exception`; any failure returns a `DecisionResponse` with `outcome=HUMAN_REVIEW`, populated `errors` and `reasoning` fields, and never re-raises. A global outer try/catch around `run_integrated_pipeline` guarantees even catastrophic failures resolve to HUMAN_REVIEW.
- **Agent 2 orchestrator (`agent2/workflow/orchestrator.py`)**: Implements a state machine (`INIT` → `RECEIVED` → `VALIDATING` → … → `APPROVED` / `BLOCKED` / `HUMAN_REVIEW` / `FAILED`). Errors do not raise; they call `AuditLogger.log_transition(..., "FAILED"|"BLOCKED"|"HUMAN_REVIEW", ...)` and return an `Agent2Result` carrying `status`, `missing_information`, and `human_review_required`.
- **Audit logger (`agent2/audit/audit_logger.py`)**: Persists every state transition (including error transitions) to SQLite via `AuditRepository` and prints a human-readable line containing `correlation_id`, claim ID, version, before/after states, action, result, and error message.
- **Validators (`agent2/validators/*.py`, `rag/validation/output_validator.py`, `decision/agent.py`)**: Return lists of error strings (`ClaimValidator.validate_claim`) or raise `ValueError` with descriptive messages when LLM output violates the criterion-assessment contract (e.g., duplicate assessments, uncited evidence paths, unsupported status combinations).
- **Adapters (`adapters/rag_adapter.py`, `adapters/runtime_adapter.py`)**: Raise `ValueError` for null inputs (`runtime_policy`, `canonical_claim`, `claim_output`, `provider_claim`) and use `try/except ValueError` / `try/except json.JSONDecodeError` / `try/except (TypeError, ValueError)` for defensive parsing of optional fields.
- **Decision agent (`decision/agent.py`)**: `_validate_criterion_assessments` raises `ValueError` for every contract violation (duplicate IDs, missing canonical paths, unsupported status/evidence-path combos). These propagate up to the integrated pipeline's catch-all, which converts them to HUMAN_REVIEW.

## Architecture and Conventions

### 1. Fail-closed by default
Every recoverable path in `services/integrated_pipeline.py` catches `Exception` and returns a safe `DecisionResponse` rather than bubbling up. The comment explicitly calls this out: *"Catch-all safe fail-closed: return DecisionResponse with HUMAN_REVIEW outcome"*. This means the system treats unexpected failures as human-review escalations instead of crashes.

### 2. Structured error propagation through result objects
Business logic does not throw domain exceptions outward. Instead:
- `Agent2Result` carries `status`, `validation_status`, `policy_status`, `evidence_status`, `missing_information`, `human_review_required`, and `submission_package`.
- `DecisionResponse` carries `outcome`, `reasoning`, `exclusion_results`, `criteria_results`, `criteria_evaluations`, `evidence_status`, and `errors`.
- `Agent2V1Result` carries `final_outcome`, `final_decision`, `versions`, `submissions`, `resubmissions`, `human_review_required`, `human_review_reasons`, `sensitive_blocked`, and `audit_trail`.
Callers inspect these fields rather than catching exceptions.

### 3. Audit trail for every error
In Agent 2, each error path calls `logger.log_transition(claim_id, version, state, next_state, ..., error=...)` before returning. The `error` field captures the exception message or a human-readable reason. This creates a persistent, queryable record of what went wrong per claim version.

### 4. Input validation via Pydantic + explicit checks
- All request bodies use Pydantic models (`ClaimInput`, `CanonicalClaim`, `CriterionAssessment`, etc.) with `model_config = {"extra": "forbid"}` so unknown fields cause `ValidationError` immediately.
- Business functions add additional semantic checks and raise `ValueError` with specific messages (e.g., `"LLM returned duplicate criterion assessments."`, `"MISSING assessments must cite a required evidence expectation."`).
- The API layer translates `ValidationError` to `HTTPException(422, detail=ve.errors())`.

### 5. Defensive parsing with fallbacks
Where JSON or numeric fields may be malformed, code uses `try/except (TypeError, ValueError)` or `try/except json.JSONDecodeError` and falls back to defaults (e.g., setting `attempt` to 2 if it cannot be parsed as int). This prevents one bad field from crashing the whole pipeline.

### 6. No custom exception classes
There is no `errors/` package and no custom exception hierarchy. Domain errors are expressed as:
- `ValueError` / `FileNotFoundError` for contract violations raised inside functions.
- `HTTPException` only at the FastAPI boundary.
- Structured result objects (`Agent2Result`, `DecisionResponse`, `Agent2V1Result`) for normal error signaling within the pipeline.

### 7. Recovery loops bound by configuration
Resubmission attempts are bounded by `MAX_RESUBMISSION_ATTEMPTS` (imported from `config` or `agent2.config`). When exceeded, the orchestrator transitions to `HUMAN_REVIEW` and records the reason in both the audit log and `human_review_reasons`.

## Conventions and Constraints Observed

- **Every public entry point has a top-level try/except**: `api/main.py` endpoints, `services/integrated_pipeline.run_integrated_pipeline`, and `run_agent2_v1_pipeline` all wrap their bodies in broad exception handlers that convert failures into safe outputs.
- **Errors are never swallowed silently**: Even caught exceptions are recorded — printed via `print(f"[RAG Integration] Failure during RAG run... {e}")`, appended to `errors`/`reasoning` lists, or persisted through `AuditLogger.log_transition`.
- **Human review is the terminal error state**: Both `DecisionResponse` and `Agent2Result` converge on `HUMAN_REVIEW` / `HUMAN_REVIEW` status for unrecoverable problems, ensuring a human always sees failed automated decisions.
- **Validation errors are distinguished from runtime errors**: Pydantic `ValidationError` gets a 422 response; other exceptions get 500. Inside pipelines, validation failures produce structured `errors` lists rather than raising.
- **No logging framework is used**: The codebase relies on `print()` statements and the `AuditLogger` SQLite persistence. There is no `logging` module usage in the core modules.
- **Recovery is source-restricted**: Agent 2 recovery reads only from the provider-side evidence pool (never payer data), enforced by `_default_recovery_source_factory` and provenance checks against the pool — a design constraint that also acts as an anti-fabrication guard.