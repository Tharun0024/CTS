"""Agent1 -> Agent2 structured evidence-request boundary (Phase 2).

Frozen V1 routing:
  APPROVE                   -> terminal, Agent2 NOT invoked (returns None)
  REJECT (hard/coverage)    -> terminal, Agent2 NOT invoked (returns None).
                               There is NO generic REJECT -> Agent2 rule.
  HUMAN_REVIEW              -> human workflow, Agent2 NOT directly invoked.
  REQUEST_MORE_INFORMATION  -> the ONLY outcome routed to Agent2 recovery.

The recovery handler searches ONLY the provider-side clinical data interface
(PatientEvidenceRetriever over the provider SQLite warehouse). It never
touches payer-side data, never fabricates evidence, never marks a criterion
SATISFIED, and never emits a coverage decision.
"""

import re
import uuid
from typing import Dict, List, Optional

from decision.schemas import DecisionOutcome, DecisionResponse

from ..retrieval.patient_retriever import PatientEvidenceRetriever
from ..schemas.evidence import Evidence, EvidenceState
from ..schemas.evidence_request import (
    EvidenceProvenanceRef,
    EvidenceRecoveryResult,
    EvidenceRequest,
    RequestedItemResult,
    RequestedItemState,
)

# Deterministic clinical-concept rules (mirrors RejectionAnalyzer's keyword
# mapping without any LLM involvement, keeping recovery reproducible).
_CONCEPT_RULES = [
    ("ldl", ("ldl", "cholesterol", "lipid")),
    ("statin", ("statin", "simvastatin", "atorvastatin", "rosuvastatin")),
    ("hemoglobin", ("hemoglobin",)),
    ("hba1c", ("hba1c", "a1c")),
    ("iron", ("iron", "ferrous", "ferritin")),
    ("metformin", ("metformin",)),
    ("physical therapy", ("physical therapy", "physiotherapy", "conservative therapy")),
    ("imaging", ("imaging", "x-ray", "xray", "radiograph", "mri", "ct scan")),
]

# Phase-1 requested_information format: "<name> (<criterion_id>): <evidence_key>"
_REQUEST_FORMAT_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<criterion>[^)]+)\)\s*:\s*(?P<key>.+)$")


def _parse_request_text(text: str) -> Dict[str, Optional[str]]:
    """Extract criterion_id/evidence_key from Agent1's structured request line."""
    match = _REQUEST_FORMAT_RE.match(text.strip())
    if match:
        return {
            "criterion_id": match.group("criterion").strip() or None,
            "evidence_key": match.group("key").strip() or None,
        }
    return {"criterion_id": None, "evidence_key": None}


def _concepts_for_text(text: str) -> List[str]:
    """Deterministic mapping of one request line to provider-DB search concepts."""
    text_lower = text.lower()
    concepts = [
        concept for concept, keywords in _CONCEPT_RULES
        if any(kw in text_lower for kw in keywords)
    ]
    return concepts


def _requested_items_from_decision(
    decision_response: DecisionResponse,
) -> tuple:
    """Extract (requested_information, criterion_ids, evidence_keys) from one
    Agent1 decision. requested_information keeps Agent1's structured lines;
    criterion_ids/evidence_keys are gathered from MISSING evaluations and
    missing evidence statuses, plus keys parsed from the request lines."""
    criterion_ids = sorted({
        criterion_id
        for criterion_id, evaluation in (decision_response.criteria_evaluations or {}).items()
        if evaluation.state == "MISSING"
    })
    evidence_keys = sorted({
        key for key, status in (decision_response.evidence_status or {}).items()
        if status == "missing"
    })
    # Evidence keys embedded in structured requested_information lines.
    for text in decision_response.requested_information or []:
        parsed = _parse_request_text(text)
        if parsed["evidence_key"] and parsed["evidence_key"] not in evidence_keys:
            evidence_keys.append(parsed["evidence_key"])
        if parsed["criterion_id"] and parsed["criterion_id"] not in criterion_ids:
            criterion_ids.append(parsed["criterion_id"])
    evidence_keys = sorted(evidence_keys)
    criterion_ids = sorted(criterion_ids)

    requested_information = list(decision_response.requested_information or [])
    if not requested_information:
        # Fall back to bare evidence keys so the request still carries content.
        requested_information = list(evidence_keys)
    return requested_information, criterion_ids, evidence_keys


def route_agent1_decision(
    decision_response: DecisionResponse,
    patient_id: str,
    claim_version: int,
    correlation_id: Optional[str] = None,
) -> Optional[EvidenceRequest]:
    """Frozen V1 routing gate: convert an Agent1 decision into the structured
    evidence request Agent2 consumes -- ONLY for REQUEST_MORE_INFORMATION.

    Returns None for APPROVE, every REJECT (hard denial / coverage exclusion),
    and HUMAN_REVIEW. Agent2 is never invoked for those outcomes.
    """
    if decision_response.outcome != DecisionOutcome.REQUEST_MORE_INFORMATION:
        return None
    if not decision_response.agent2_recoverable:
        # Contract guard: only the Agent2-recoverable outcome may route here.
        return None

    claim_id = decision_response.claim_id or decision_response.case_id
    requested_information, criterion_ids, evidence_keys = _requested_items_from_decision(
        decision_response
    )

    if not (requested_information or evidence_keys or criterion_ids):
        # Nothing recoverable was requested; do not invoke Agent2.
        return None

    return EvidenceRequest(
        claim_id=claim_id,
        claim_version=claim_version,
        patient_id=patient_id,
        evidence_request_id=f"ERQ-{uuid.uuid4().hex[:10].upper()}",
        correlation_id=correlation_id or f"CORR-{claim_id}-V{claim_version}",
        requested_information=requested_information,
        criterion_ids=criterion_ids,
        evidence_keys=evidence_keys,
        policy_id=decision_response.policy_id,
        source_reason_code=(
            decision_response.reason_code.value
            if decision_response.reason_code is not None else None
        ),
    )


class EvidenceRecoveryHandler:
    """Provider-side recovery for one structured EvidenceRequest.

    Guarantees:
      - Retrieves ONLY through the provider-side clinical data interface.
      - Tracks each requested item as FOUND or MISSING (never SATISFIED).
      - Preserves real evidence IDs and provenance for FOUND items.
      - Never fabricates evidence: MISSING items carry no evidence references
        and recovered_evidence contains only real FOUND records.
      - Preserves claim/version identity and correlation IDs in the result.
      - Makes no coverage decision (result carries no decision fields).
    """

    def __init__(self, retriever: Optional[PatientEvidenceRetriever] = None):
        self.retriever = retriever or PatientEvidenceRetriever()

    def process(self, request: EvidenceRequest) -> EvidenceRecoveryResult:
        # Single provider-side snapshot; all matching happens against real records.
        all_evidence = self.retriever.retrieve_all_evidence(request.patient_id)

        item_results: List[RequestedItemResult] = []
        recovered_by_id: Dict[str, Evidence] = {}
        notes: List[str] = []

        request_texts = list(request.requested_information)
        if not request_texts:
            request_texts = list(request.evidence_keys or request.criterion_ids)

        for text in request_texts:
            parsed = _parse_request_text(text)
            matches = self._match_item(text, all_evidence)

            if matches:
                provenance = [
                    EvidenceProvenanceRef(
                        evidence_id=ev.evidence_id,
                        source_type=ev.source_type,
                        source_record_id=ev.source_record_id,
                        event_date=ev.event_date or "",
                    )
                    for ev in matches
                ]
                item_results.append(
                    RequestedItemResult(
                        request_text=text,
                        criterion_id=parsed["criterion_id"],
                        evidence_key=parsed["evidence_key"],
                        state=RequestedItemState.FOUND,
                        evidence_ids=[ev.evidence_id for ev in matches],
                        provenance=provenance,
                    )
                )
                for ev in matches:
                    recovered_by_id.setdefault(ev.evidence_id, ev)
            else:
                # Genuinely absent from provider records: remains MISSING.
                # No placeholder/fabricated evidence is produced.
                item_results.append(
                    RequestedItemResult(
                        request_text=text,
                        criterion_id=parsed["criterion_id"],
                        evidence_key=parsed["evidence_key"],
                        state=RequestedItemState.MISSING,
                    )
                )

        missing_count = sum(
            1 for item in item_results if item.state == RequestedItemState.MISSING
        )
        if missing_count:
            notes.append(
                f"{missing_count} requested item(s) remain MISSING in provider "
                "records; no evidence was fabricated. Follow existing "
                "human-review/recovery rules for unresolved items."
            )
        notes.append(
            "FOUND records were retrieved but NOT evaluated for criterion "
            "satisfaction; Agent 1 owns the coverage decision."
        )

        return EvidenceRecoveryResult(
            evidence_request_id=request.evidence_request_id,
            correlation_id=request.correlation_id,
            claim_id=request.claim_id,
            claim_version=request.claim_version,
            patient_id=request.patient_id,
            item_results=item_results,
            recovered_evidence=list(recovered_by_id.values()),
            notes=notes,
        )

    def _match_item(self, text: str, all_evidence: List[Evidence]) -> List[Evidence]:
        """Match one requested item against real provider records only."""
        concepts = _concepts_for_text(text)
        matches: Dict[str, Evidence] = {}

        if concepts:
            for concept in concepts:
                for ev in self._search_concept(concept, all_evidence):
                    matches[ev.evidence_id] = ev

        if not matches:
            # Deterministic fallback: substring search on significant tokens of
            # the request text (evidence key or free-form description).
            parsed = _parse_request_text(text)
            tokens = [parsed["evidence_key"]] if parsed["evidence_key"] else []
            tokens += [
                token for token in re.split(r"\W+", text.lower()) if len(token) >= 4
            ]
            for token in tokens:
                for ev in all_evidence:
                    if token in ev.content.lower():
                        matches[ev.evidence_id] = ev

        result = list(matches.values())
        # Only real FOUND records may leave the provider boundary.
        return [ev for ev in result if ev.state == EvidenceState.FOUND]

    @staticmethod
    def _search_concept(concept: str, all_evidence: List[Evidence]) -> List[Evidence]:
        """Concept search mirroring PatientEvidenceRetriever's deterministic rules."""
        lowered = [(ev, ev.content.lower()) for ev in all_evidence]
        if concept == "ldl":
            return [ev for ev, content in lowered if "ldl" in content or "18262-6" in content]
        if concept == "statin":
            terms = ["simvastatin", "atorvastatin", "rosuvastatin", "statin"]
            return [ev for ev, content in lowered if any(t in content for t in terms)]
        if concept == "hemoglobin":
            return [ev for ev, content in lowered if "hemoglobin" in content or "718-7" in content]
        if concept == "hba1c":
            return [ev for ev, content in lowered if "hba1c" in content or "4548-4" in content]
        if concept == "iron":
            return [ev for ev, content in lowered if "iron" in content or "ferrous" in content or "ferritin" in content]
        if concept == "metformin":
            return [ev for ev, content in lowered if "metformin" in content]
        if concept == "physical therapy":
            terms = ["physical therapy", "physiotherapy", "rehabilitation"]
            return [ev for ev, content in lowered if any(t in content for t in terms)]
        if concept == "imaging":
            terms = ["x-ray", "xray", "radiograph", "mri", "ct", "imaging", "ultrasound"]
            return [ev for ev, content in lowered if any(t in content for t in terms)]
        return []
