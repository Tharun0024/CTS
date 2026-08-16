"""Agent 2 recovery package (Phase 2).

Agent1 -> Agent2 evidence-request boundary:
  - route_agent1_decision: frozen V1 routing gate (only
    REQUEST_MORE_INFORMATION produces an EvidenceRequest).
  - EvidenceRecoveryHandler: provider-side evidence recovery tracking each
    requested item as FOUND or MISSING with real evidence IDs/provenance.
"""

from .evidence_recovery import EvidenceRecoveryHandler, route_agent1_decision

__all__ = ["EvidenceRecoveryHandler", "route_agent1_decision"]
