"""Agent 2 recovery package (Phase 2 + Phase 3).

Agent1 -> Agent2 evidence-request boundary:
  - route_agent1_decision: frozen V1 routing gate (only
    REQUEST_MORE_INFORMATION produces an EvidenceRequest).
  - EvidenceRecoveryHandler: provider-side evidence recovery tracking each
    requested item as FOUND or MISSING with real evidence IDs/provenance.

Phase 3 recovery/resubmission workflow:
  - run_contract_recovery: contract-driven recovery over the canonical
    provider evidence pool (EvidenceRequest -> FOUND/MISSING -> selected
    real pool records for the release gate / resubmission).
"""

from .evidence_recovery import EvidenceRecoveryHandler, route_agent1_decision
from .resubmission_workflow import (
    CanonicalPoolRetriever,
    RecoveryPlan,
    build_evidence_request_for_recovery,
    canonical_pool_to_evidence,
    run_contract_recovery,
)

__all__ = [
    "EvidenceRecoveryHandler",
    "route_agent1_decision",
    "CanonicalPoolRetriever",
    "RecoveryPlan",
    "build_evidence_request_for_recovery",
    "canonical_pool_to_evidence",
    "run_contract_recovery",
]
