"""Request/response payload models for the claims API boundary (Phase 5A).

Responses are intentionally plain dicts produced by the mapping layer (the
claim record is the contract); only request bodies are validated here.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CreateClaimRequest(BaseModel):
    """Create + process one claim through the real V1 pipeline.

    Two input modes:
      1. ``canonical_claim`` passthrough — a full Version-1 CanonicalClaim
         (must carry claim_id, case_data, evidence). Used by integrations
         that already speak the canonical contract.
      2. Structured fields (frontend CreateClaimPayload-compatible) — the
         service assembles the canonical claim from these.
    """

    canonical_claim: Optional[Dict[str, Any]] = None

    claim_id: Optional[str] = None
    patient_id: str = "PAT-UNSPECIFIED"
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    payer: Optional[str] = None
    policy_id: Optional[str] = None
    procedure_code: Optional[str] = None
    procedure: Optional[str] = None
    diagnosis_codes: List[str] = Field(default_factory=list)
    service_date: Optional[str] = None
    provider_id: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    clinical_metrics: Dict[str, Any] = Field(default_factory=dict)

    # V1 execution knobs (pipeline defaults apply when omitted).
    provider_decision: Literal["ACCEPT", "DECLINE"] = "ACCEPT"
    max_resubmissions: Optional[int] = Field(default=None, ge=0)


class ProviderDecisionRequest(BaseModel):
    """Provider accept/decline consent on recovered evidence."""

    decision: Literal["ACCEPT", "DECLINE"]
    reason: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class HumanResolutionRequest(BaseModel):
    """Human resolution of a HUMAN_REVIEW hold.

    The claim re-enters NORMAL Agent 1 routing afterwards; there is no direct
    recovery shortcut. Attached evidence must be real provider records with
    evidence_id (fabricated entries are rejected by the pipeline).
    """

    resolution_note: str = ""
    attached_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    # Phase 3: only the hospital portal may resolve a human review; any other
    # portal (e.g. "insurance") is read-only for this state and gets a 403.
    resolved_by: str = "hospital"
