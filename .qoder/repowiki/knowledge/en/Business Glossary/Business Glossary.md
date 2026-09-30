---
kind: business_term
name: Business Glossary
category: business_term
scope:
    - '**'
---

### Agent1
- Definition：The deterministic clinical decision engine in `decision/` that evaluates a CanonicalClaim against RAG-retrieved policy criteria and returns a DecisionResponse with outcomes APPROVE, REJECT, REQUEST_MORE_INFORMATION, or HUMAN_REVIEW. It never accesses the Big Patient Record directly and must not be duplicated in the Agent2 loop.
- Aliases：DecisionAgent、deterministic agent

### Agent2
- Definition：The recovery layer (`agent2/`) that runs after Agent1 when the outcome is recoverable (missing evidence, failed criteria). It retrieves additional provider-side evidence, builds a new claim version (V2+), enforces sensitivity/release gates and anti-fabrication provenance checks, then re-invokes Agent1. It must never access payer-side data or make coverage decisions itself.
- Aliases：recovery agent、resubmission agent

### CanonicalClaim
- Definition：The stable domain-model contract (`transformation/canonical_claim.py`) representing a prior authorization claim after normalization from runtime/provider/payer sources. All downstream components (RAG, Agent1, Agent2) operate on this shape; versions are immutable snapshots appended as V1→V2→….
- Aliases：claim model、normalized claim

### Big Patient Record
- Definition：The provider-side SQLite database (`agent2/database/db_manager.py`) containing patients, conditions, medications, observations, procedures, encounters, and documents. Agent2 may read it for evidence recovery; Agent1 and the RAG pipeline must never query it directly.
- Aliases：provider DB、patient record

### SubmissionPackage
- Definition：The minimal set of evidence and metadata assembled for resubmission (built by `agent2/submission/package_builder.py` and referenced in `services/integrated_pipeline.py`). Each V2+ version carries a `new_evidence_delta` listing only the newly added evidence IDs.
- Aliases：resubmission package、delta package

### HUMAN_REVIEW
- Definition：A terminal outcome meaning the claim cannot be auto-resolved and requires manual medical-director review. In the V1 routing contract it is terminal for both Agent1 and Agent2: no direct Agent2 recovery is attempted from HUMAN_REVIEW, and administrative blocks (lapsed eligibility, filing deadline exceeded) force HUMAN_REVIEW without recovery.
- Aliases：human review、manual review

### MAX_RESUBMISSION_ATTEMPTS
- Definition：The hard cap on how many times Agent2 may attempt recovery and resubmit (default 3, defined in `agent2/config.py`). When reached the pipeline stops safely and escalates to HUMAN_REVIEW without overwriting history.
- Aliases：resubmission limit、attempt cap

### Sensitivity release gate
- Definition：Programmatic rule enforcing that only evidence marked `ROUTINE` may be released automatically; `PROTECTED_*` and `UNKNOWN` sensitivity values block the evidence and force HUMAN_REVIEW. Implemented in `services/integrated_pipeline.py::_release_gate` and enforced before any recovered evidence enters a resubmission.
- Aliases：release gate、sensitivity gate、programmatic release gate

### Immutable claim versions
- Definition：Policy that claim snapshots are append-only: V1 stays untouched, each recovery creates a new V2/V3 snapshot with `new_evidence_delta` identifying only the added records. Derived fields (diagnoses, clinical_metrics) are rebuilt for the new evidence set; recovered facts take precedence over previously derived metric values.
- Aliases：versioned claims、append-only history

### Anti-fabrication provenance guard
- Definition：Safety rule ensuring every piece of recovered evidence included in a resubmission actually exists in the provider pool (by `evidence_id`); no fabricated or invented IDs may enter any version. Enforced in `_select_recovered_evidence` and the provenance check before building the next version.
- Aliases：provenance guard、fabrication protection
