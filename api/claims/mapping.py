"""Contract mapping between backend V1 semantics and the frontend contract.

Pure mapping/serialization only — NO business logic and NO routing decisions
live here. Backend enums and frozen routing semantics stay untouched; this
module only translates names and serializes immutable workflow artifacts:

  DecisionOutcome             -> frontend decision status
      APPROVE                 -> ACCEPT
      REJECT                  -> REJECT
      REQUEST_MORE_INFORMATION-> MORE_INFORMATION
      HUMAN_REVIEW            -> HUMAN_REVIEW

  ClaimWorkflowState          -> frontend ClaimStatus
      APPROVED                -> ACCEPTED
      REJECTED                -> REJECTED
      HUMAN_REVIEW/FAILED     -> HUMAN_REVIEW
      ROUTED_RECOVERY/RECOVERING -> UNDER_REVIEW
      AWAITING_PROVIDER_DECISION -> MORE_INFO
      RESUBMITTING            -> SUBMITTED_AGAIN
      RECEIVED                -> SUBMITTED
      EVALUATING/RESOLVED_REENTRY -> PROCESSING
      INIT                    -> DRAFT
"""

from typing import Any, Dict, List, Optional

from decision.schemas import DecisionOutcome, DecisionResponse
from agent2.workflow.control_plane import (
    ClaimWorkflowState,
    ProviderDecisionRecord,
    WorkflowEvent,
)


# Backend decision outcome -> frontend decision status (types/claim.ts)
DECISION_TO_FRONTEND: Dict[DecisionOutcome, str] = {
    DecisionOutcome.APPROVE: "ACCEPT",
    DecisionOutcome.REJECT: "REJECT",
    DecisionOutcome.REQUEST_MORE_INFORMATION: "MORE_INFORMATION",
    DecisionOutcome.HUMAN_REVIEW: "HUMAN_REVIEW",
}

# Backend workflow state -> frontend claim status (types/claim.ts ClaimStatus)
WORKFLOW_STATE_TO_CLAIM_STATUS: Dict[ClaimWorkflowState, str] = {
    ClaimWorkflowState.INIT: "DRAFT",
    ClaimWorkflowState.RECEIVED: "SUBMITTED",
    ClaimWorkflowState.EVALUATING: "PROCESSING",
    ClaimWorkflowState.ROUTED_RECOVERY: "UNDER_REVIEW",
    ClaimWorkflowState.RECOVERING: "UNDER_REVIEW",
    ClaimWorkflowState.AWAITING_PROVIDER_DECISION: "MORE_INFO",
    ClaimWorkflowState.RESUBMITTING: "SUBMITTED_AGAIN",
    ClaimWorkflowState.APPROVED: "ACCEPTED",
    ClaimWorkflowState.REJECTED: "REJECTED",
    ClaimWorkflowState.HUMAN_REVIEW: "HUMAN_REVIEW",
    ClaimWorkflowState.RESOLVED_REENTRY: "PROCESSING",
    # Fail-closed system failures surface as human review, never as approval.
    ClaimWorkflowState.FAILED: "HUMAN_REVIEW",
}


def map_decision_status(outcome: DecisionOutcome) -> str:
    return DECISION_TO_FRONTEND.get(outcome, str(outcome.value))


def map_claim_status(state: ClaimWorkflowState) -> str:
    return WORKFLOW_STATE_TO_CLAIM_STATUS.get(state, str(state.value))


def derive_evidence_request_status(
    state: ClaimWorkflowState, has_request: bool
) -> str:
    """Frontend EvidenceRequestStatus derived from the workflow state.

    Pure mapping: the lifecycle itself is owned by the control plane.
    """
    if not has_request:
        return "CLOSED"
    if state in (ClaimWorkflowState.ROUTED_RECOVERY, ClaimWorkflowState.RECOVERING):
        return "PENDING_PROVIDER_RESPONSE"
    if state == ClaimWorkflowState.AWAITING_PROVIDER_DECISION:
        return "WAITING_FOR_PROVIDER"
    if state == ClaimWorkflowState.RESUBMITTING:
        return "RECEIVED"
    # Terminal / HUMAN_REVIEW / RESOLVED_REENTRY: the request is concluded.
    return "CLOSED"


# ---------------------------------------------------------------------------
# Serializers (immutable artifacts -> JSON-safe dicts)
# ---------------------------------------------------------------------------

def serialize_decision(decision: Optional[DecisionResponse]) -> Optional[Dict[str, Any]]:
    if decision is None:
        return None
    reason_code = getattr(decision, "reason_code", None)
    return {
        "outcome": decision.outcome.value,                 # backend truth
        "status": map_decision_status(decision.outcome),   # frontend contract
        "reason_code": reason_code.value if hasattr(reason_code, "value") else reason_code,
        "reasoning": list(decision.reasoning or []),
        "agent2_recoverable": bool(decision.agent2_recoverable),
        "requested_information": list(decision.requested_information or []),
    }


def serialize_event(event: WorkflowEvent) -> Dict[str, Any]:
    return {
        "seq": event.seq,
        "claim_id": event.claim_id,
        "claim_version": event.claim_version,
        "state_before": event.state_before,
        "state_after": event.state_after,
        "action": event.action,
        "correlation_id": event.correlation_id,
        "evidence_request_id": event.evidence_request_id,
        "detail": event.detail,
        "timestamp": event.timestamp,
    }


def serialize_provider_decision(record: ProviderDecisionRecord) -> Dict[str, Any]:
    return {
        "decision_id": record.decision_id,
        "claim_id": record.claim_id,
        "claim_version": record.claim_version,
        "decision": record.decision,
        "evidence_ids": list(record.evidence_ids),
        "evidence_request_id": record.evidence_request_id,
        "correlation_id": record.correlation_id,
        "reason": record.reason,
        "decided_at": record.decided_at,
    }


def serialize_evidence_request(request: Optional[Any]) -> Optional[Dict[str, Any]]:
    if request is None:
        return None
    return {
        "evidence_request_id": request.evidence_request_id,
        "correlation_id": request.correlation_id,
        "claim_id": request.claim_id,
        "claim_version": request.claim_version,
        "patient_id": request.patient_id,
        "requested_information": list(request.requested_information or []),
        "criterion_ids": list(request.criterion_ids or []),
        "evidence_keys": list(request.evidence_keys or []),
        "policy_id": request.policy_id,
        "source_reason_code": request.source_reason_code,
        "created_at": request.created_at,
    }


def serialize_recovery_result(result: Optional[Any]) -> Optional[Dict[str, Any]]:
    if result is None:
        return None
    return {
        "evidence_request_id": result.evidence_request_id,
        "correlation_id": result.correlation_id,
        "claim_id": result.claim_id,
        "claim_version": result.claim_version,
        "patient_id": result.patient_id,
        "item_results": [
            {
                "request_text": item.request_text,
                "criterion_id": item.criterion_id,
                "evidence_key": item.evidence_key,
                "state": item.state.value,   # FOUND | MISSING only (no SATISFIED)
                "evidence_ids": list(item.evidence_ids),
            }
            for item in result.item_results
        ],
        "recovered_evidence_ids": [ev.evidence_id for ev in result.recovered_evidence],
        "notes": list(result.notes or []),
    }


def serialize_version(version: Dict[str, Any]) -> Dict[str, Any]:
    claim = version.get("claim") or {}
    decision = version.get("decision")
    return {
        "version": version.get("version"),
        "attempt": version.get("attempt"),
        "decision": serialize_decision(decision),
        "new_evidence_delta": list(version.get("new_evidence_delta") or []),
        "evidence_ids": [
            item.get("evidence_id") for item in claim.get("evidence", []) if isinstance(item, dict)
        ],
        "patient_age": (claim.get("case_data") or {}).get("patient_age"),
    }


def serialize_submission(submission: Dict[str, Any]) -> Dict[str, Any]:
    """Pipeline submission dicts carry version/attempt + contract IDs.

    A stable ``submission_id`` is derived deterministically
    (``SUB-{claim_id}-{version}``) so resubmissions stay individually
    addressable without altering workflow logic.
    """
    version_label = submission.get("version")
    claim_version = submission.get("claim_version")
    if claim_version is None and isinstance(version_label, str) and version_label.startswith("V"):
        try:
            claim_version = int(version_label[1:])
        except ValueError:
            claim_version = None
    submission_id = submission.get("submission_id")
    if not submission_id and submission.get("claim_id") and version_label:
        submission_id = f"SUB-{submission['claim_id']}-{version_label}"
    return {
        "submission_id": submission_id,
        "claim_id": submission.get("claim_id"),
        "claim_version": claim_version,
        "version": version_label,
        "attempt": submission.get("attempt"),
        "evidence_ids": list(submission.get("evidence_ids") or []),
        "new_evidence_delta": list(submission.get("new_evidence_delta") or []),
        "released": submission.get("released"),
        "correlation_id": submission.get("correlation_id"),
        "evidence_request_id": submission.get("evidence_request_id"),
    }
