"""Agent 2 evidence-request contract (Phase 2).

Defines the structured REQUEST_MORE_INFORMATION payload Agent 2 receives from
Agent 1, and the provider-side evidence recovery result Agent 2 produces.

Frozen V1 semantics enforced here:
  - Agent 2 receives ONLY the structured evidence request (never payer-side
    data or the full Agent 1 decision internals).
  - Each requested item is tracked as FOUND or MISSING. There is deliberately
    no SATISFIED state: FOUND evidence does NOT mean the criterion is
    SATISFIED. Only Agent 1 decides criterion satisfaction / coverage.
  - MISSING items stay MISSING; Agent 2 never fabricates evidence.
  - Claim/version identity and correlation IDs are preserved end-to-end.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from .evidence import Evidence


class RequestedItemState(str, Enum):
    """Retrieval state of one requested evidence item.

    FOUND: real provider-side records matching the request were located.
    MISSING: nothing matching exists in the provider clinical data.

    NOTE: intentionally no SATISFIED member. FOUND != SATISFIED; criterion
    satisfaction is exclusively Agent 1's (payer-side) determination.
    """
    FOUND = "FOUND"
    MISSING = "MISSING"


class EvidenceRequest(BaseModel):
    """Structured evidence request consumed by Agent 2.

    Produced from Agent 1's DecisionResponse ONLY when the outcome is
    REQUEST_MORE_INFORMATION (the sole Agent2-recoverable outcome).
    """
    claim_id: str = Field(min_length=1)
    claim_version: int = Field(ge=1)
    patient_id: str = Field(min_length=1)
    evidence_request_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    requested_information: List[str] = Field(
        default_factory=list,
        description="Policy-defined documentation requests from Agent 1",
    )
    criterion_ids: List[str] = Field(
        default_factory=list,
        description="Criterion identifiers in MISSING state, where available",
    )
    evidence_keys: List[str] = Field(
        default_factory=list,
        description="Evidence keys requested by Agent 1, where available",
    )
    policy_id: Optional[str] = None
    source_reason_code: Optional[str] = Field(
        default=None,
        description="Agent 1 DecisionReasonCode that produced this request",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    @model_validator(mode="after")
    def require_request_content(self) -> "EvidenceRequest":
        if not (self.requested_information or self.evidence_keys or self.criterion_ids):
            raise ValueError(
                "EvidenceRequest must carry at least one of requested_information, "
                "evidence_keys, or criterion_ids."
            )
        return self


class EvidenceProvenanceRef(BaseModel):
    """Real provenance of one recovered provider-side record."""
    evidence_id: str
    source_type: str
    source_record_id: str
    event_date: str = ""


class RequestedItemResult(BaseModel):
    """Per-requested-item recovery outcome.

    Carries retrieval state + real evidence references only. No satisfaction,
    eligibility, or coverage fields: Agent 2 never makes coverage decisions.
    """
    request_text: str
    criterion_id: Optional[str] = None
    evidence_key: Optional[str] = None
    state: RequestedItemState
    evidence_ids: List[str] = Field(default_factory=list)
    provenance: List[EvidenceProvenanceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_found_requires_real_ids(self) -> "RequestedItemResult":
        """FOUND requires real evidence IDs/provenance; MISSING must carry none."""
        if self.state == RequestedItemState.FOUND and not self.evidence_ids:
            raise ValueError("FOUND item must reference at least one real evidence ID.")
        if self.state == RequestedItemState.MISSING and (self.evidence_ids or self.provenance):
            raise ValueError("MISSING item must not reference evidence (no fabrication).")
        return self


class EvidenceRecoveryResult(BaseModel):
    """Provider-side recovery result returned by Agent 2.

    Contains NO coverage decision. Routing of the result back into the
    submission lifecycle belongs to the orchestrator / Agent 1 re-evaluation.
    """
    evidence_request_id: str
    correlation_id: str
    claim_id: str
    claim_version: int
    patient_id: str
    item_results: List[RequestedItemResult] = Field(default_factory=list)
    recovered_evidence: List[Evidence] = Field(
        default_factory=list,
        description="Only real FOUND provider-side records (real IDs, provenance)",
    )
    notes: List[str] = Field(default_factory=list)

    @property
    def all_requested_found(self) -> bool:
        return bool(self.item_results) and all(
            item.state == RequestedItemState.FOUND for item in self.item_results
        )

    @property
    def missing_requests(self) -> List[str]:
        return [
            item.request_text
            for item in self.item_results
            if item.state == RequestedItemState.MISSING
        ]
