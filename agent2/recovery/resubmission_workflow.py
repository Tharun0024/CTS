"""Phase 3: recovery/resubmission workflow on top of the Phase-2 contract.

Connects the structured EvidenceRequest contract to the real Agent2
recovery/resubmission workflow:

    Agent1 REQUEST_MORE_INFORMATION (the ONLY Agent2-recoverable outcome;
    documentation insufficiency is always represented as RMI by Agent 1)
    -> EvidenceRequest (structured, request-only; no payer internals)
    -> provider-side retrieval over the canonical provider evidence pool
    -> per-requested-item FOUND / MISSING tracking
    -> result handed to the sensitivity/release gate + provider
       accept/decline + versioned resubmission owned by the pipeline.

Guarantees preserved from Phase 2:
  - Provider-side data only; the payer DB is never accessed.
  - Real evidence IDs and provenance only; nothing is ever fabricated.
  - FOUND != SATISFIED; no coverage decision is made here.
  - Claim/version identity and correlation IDs are preserved end-to-end.
  - Frozen routing: REJECT (any reason) and HUMAN_REVIEW never enter this
    workflow; there is no generic REJECT -> Agent2 path.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from decision.schemas import DecisionResponse

from ..retrieval.patient_retriever import PatientEvidenceRetriever
from ..schemas.evidence import Evidence, EvidenceState
from ..schemas.evidence_request import EvidenceRecoveryResult, EvidenceRequest
from .evidence_recovery import EvidenceRecoveryHandler


def canonical_pool_to_evidence(pool: List[Dict[str, Any]]) -> List[Evidence]:
    """Adapt canonical provider-pool evidence items (dicts) to agent2 Evidence.

    Only items physically present in the provider pool can ever be converted,
    so this step can never fabricate evidence. Items lacking an evidence_id
    are skipped (they cannot carry real provenance).
    """
    adapted: List[Evidence] = []
    for item in pool or []:
        if not isinstance(item, dict):
            continue
        evidence_id = item.get("evidence_id")
        if not evidence_id:
            continue
        facts = item.get("extracted_facts") or {}
        text = str(item.get("unstructured_text") or facts.get("content_reference") or "")
        # Prefix the evidence key so key-based requests remain matchable when
        # the record carries no free-text content (still real record identity).
        content = f"{item.get('evidence_key')}: {text}" if item.get("evidence_key") else text
        adapted.append(
            Evidence(
                evidence_id=str(evidence_id),
                patient_id="",  # resolved per-request by the recovery caller
                source_type=str(item.get("source") or "provider_pool"),
                source_record_id=str(facts.get("source_record_id") or evidence_id),
                event_date=str(facts.get("event_date") or ""),
                content=content,
                state=EvidenceState.FOUND,
                relevance_score=float(item.get("confidence_score") or 1.0),
                evidence_type=str(facts.get("evidence_type") or "PROVIDER_RECORD"),
                retrieved_at=str(facts.get("event_date") or ""),
            )
        )
    return adapted


class CanonicalPoolRetriever(PatientEvidenceRetriever):
    """Provider-side retrieval interface over a canonical evidence pool.

    Satisfies the same retrieval contract as PatientEvidenceRetriever but
    reads from the provider pool supplied by the orchestration layer (itself
    sourced exclusively from the provider database), never from payer data.
    """

    def __init__(self, pool: Optional[List[Dict[str, Any]]] = None, patient_id: str = ""):
        # Deliberately no super().__init__(): no DB repository is created, so
        # this retriever structurally cannot touch any database but the pool.
        self._pool = list(pool or [])
        self._patient_id = patient_id

    def retrieve_all_evidence(self, patient_id: str) -> List[Evidence]:
        evidence = canonical_pool_to_evidence(self._pool)
        for ev in evidence:
            ev.patient_id = patient_id or self._patient_id
        return evidence


def build_evidence_request_for_recovery(
    decision: DecisionResponse,
    patient_id: str,
    claim_version: int,
    correlation_id: Optional[str] = None,
) -> Optional[EvidenceRequest]:
    """Build the structured EvidenceRequest for an Agent1 decision (frozen V1).

    ONLY REQUEST_MORE_INFORMATION produces a request (delegates to the Phase-2
    routing gate route_agent1_decision). Documentation insufficiency is always
    represented as REQUEST_MORE_INFORMATION by Agent 1; every REJECT (hard
    criterion failure or coverage exclusion) is terminal and never routed here.
    """
    from .evidence_recovery import route_agent1_decision

    return route_agent1_decision(decision, patient_id, claim_version, correlation_id)


@dataclass
class RecoveryPlan:
    """Outcome of one contract-driven recovery attempt.

    Selected items are original provider-pool records (never copies with
    invented content), so provenance and sensitivity facts stay intact for
    the downstream release gate.
    """

    request: EvidenceRequest
    result: EvidenceRecoveryResult
    selected_pool_items: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def found_evidence_ids(self) -> List[str]:
        return [ev.evidence_id for ev in self.result.recovered_evidence]


def run_contract_recovery(
    decision: DecisionResponse,
    patient_id: str,
    claim_version: int,
    pool: List[Dict[str, Any]],
    correlation_id: Optional[str] = None,
) -> Optional[RecoveryPlan]:
    """Execute Phase-2 contract recovery against the provider evidence pool.

    Returns None when the decision is not recoverable or carries no
    recoverable request content (Agent2 must then not be invoked).
    """
    request = build_evidence_request_for_recovery(
        decision, patient_id, claim_version, correlation_id
    )
    if request is None:
        return None

    retriever = CanonicalPoolRetriever(pool, patient_id=request.patient_id)
    handler = EvidenceRecoveryHandler(retriever=retriever)
    result = handler.process(request)

    found_ids = {ev.evidence_id for ev in result.recovered_evidence}
    selected = [
        item
        for item in (pool or [])
        if isinstance(item, dict) and item.get("evidence_id") in found_ids
    ]
    return RecoveryPlan(request=request, result=result, selected_pool_items=selected)
