"""Claim service: the API boundary over the existing V1 workflow (Phase 5A).

Orchestration ONLY — every decision, routing rule, state transition and
lifecycle invariant lives in the existing layers:
  - services/integrated_pipeline.py  (run_agent2_v1_pipeline,
    reenter_after_human_resolution, frozen RMI/REJECT/APPROVE routing)
  - agent2/workflow/control_plane.py (legal states/transitions, audit events,
    provider decision records)

This service:
  - builds a Version-1 CanonicalClaim from the request,
  - runs the REAL pipeline on the shared control plane,
  - serializes the immutable artifacts (versions, submissions, evidence
    request, timeline, provider decisions) through api.claims.mapping,
  - persists through repository INTERFACES only (api.persistence), so cloud
    storage can later replace SQLite without touching workflow logic.

Frozen semantics preserved end-to-end:
  APPROVE -> terminal | REJECT -> held in HUMAN_REVIEW for human
  cross-verification (Phase 3; original rejection immutable) | 
  REQUEST_MORE_INFORMATION -> Agent2 | HUMAN_REVIEW -> human resolution ->
  normal Agent1 routing (never direct recovery).
"""

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from api.persistence import (
    ClaimRecordRepository,
    InMemoryClaimRecordRepository,
    InMemoryProviderDecisionRepository,
    InMemoryWorkflowEventRepository,
    ProviderDecisionRepository,
    WorkflowEventRepository,
)

from .mapping import (
    derive_evidence_request_status,
    map_claim_status,
    serialize_decision,
    serialize_event,
    serialize_evidence_request,
    serialize_provider_decision,
    serialize_recovery_result,
    serialize_submission,
    serialize_version,
)
from .schemas import CreateClaimRequest


class ClaimNotFound(KeyError):
    """Raised when an API call targets an unknown claim_id."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClaimService:
    """Thin orchestration layer between HTTP routes and the V1 pipeline."""

    def __init__(
        self,
        components: Optional[Dict[str, Any]] = None,
        recovery_source=None,
        control_plane=None,
        claim_store: Optional[ClaimRecordRepository] = None,
        provider_decision_store: Optional[ProviderDecisionRepository] = None,
        event_store: Optional[WorkflowEventRepository] = None,
        persist_workflow_db: bool = False,
        simulation_service_locator=None,
    ):
        from agent2.workflow.control_plane import WorkflowControlPlane

        # components may be injected later (api/main.py lifespan).
        self.components = components
        self.recovery_source = recovery_source
        self.control_plane = control_plane or WorkflowControlPlane(persist_db=persist_workflow_db)
        self.claim_store = claim_store or InMemoryClaimRecordRepository()
        self.provider_decision_store = provider_decision_store or InMemoryProviderDecisionRepository()
        self.event_store = event_store or InMemoryWorkflowEventRepository()
        # Optional fallback: simulation runs keep their claims in their own
        # ClaimService instances. The locator maps claim_id -> owning service
        # so the main claims API can serve simulation-scoped claims too
        # (delegation only — no routing/business logic is affected).
        self.simulation_service_locator = simulation_service_locator

    def _owning_service(self, claim_id: str):
        """Return the ClaimService owning claim_id, or raise ClaimNotFound.

        The simulation locator is consulted FIRST: with shared persistent
        claim stores the main service's claim_store also sees simulation
        claims, but their authoritative workflow/control-plane state lives in
        the owning simulation run's service. Routing them there keeps every
        read/resolve on one control plane (no divergent live views).
        """
        if self.simulation_service_locator is not None:
            owner = self.simulation_service_locator(claim_id)
            if owner is not None and owner is not self:
                return owner
        if self.claim_store.get(claim_id) is not None:
            return self
        raise ClaimNotFound(claim_id)

    # -- create / read ------------------------------------------------------

    def create_claim(self, request: CreateClaimRequest) -> Dict[str, Any]:
        if self.components is None:
            raise RuntimeError("ClaimService components are not configured.")

        canonical = self._canonical_from_request(request)
        from services.integrated_pipeline import run_agent2_v1_pipeline

        result = run_agent2_v1_pipeline(
            canonical,
            self.components,
            recovery_source=self.recovery_source,
            max_resubmissions=request.max_resubmissions,
            provider_decision=request.provider_decision,
            control_plane=self.control_plane,
        )
        record = self._serialize_run(canonical, result)
        self.claim_store.save(record)
        self._sync_append_only(canonical["claim_id"])
        return self._with_live_views(record)

    def list_claims(self) -> List[Dict[str, Any]]:
        summaries = []
        for record in self.claim_store.list():
            decision = record.get("decision") or {}
            canonical = record.get("canonical_claim") or {}
            case_data = canonical.get("case_data") or {}
            metrics = case_data.get("clinical_metrics") or {}
            procedures = case_data.get("procedures") or []
            summaries.append({
                "claim_id": record.get("claim_id"),
                "patient_id": record.get("patient_id"),
                "status": record.get("status"),
                "workflow_state": record.get("workflow_state"),
                "decision_status": decision.get("status"),
                "decision_outcome": decision.get("outcome"),
                "claim_version": record.get("claim_version"),
                "agent2_invoked": record.get("agent2_invoked"),
                "resubmissions": record.get("resubmissions"),
                "human_verification_pending": record.get("human_verification_pending"),
                "updated_at": record.get("updated_at"),
                "procedure": metrics.get("claim_procedure") or (
                    procedures[0] if procedures else None
                ),
                "procedure_code": procedures[0] if procedures else None,
                "diagnosis_codes": list(case_data.get("diagnoses") or []),
                "service_date": (canonical.get("submission") or {}).get("date"),
                "payer": metrics.get("claim_payer"),
                "policy_id": metrics.get("claim_policy_id"),
            })
        return summaries

    def get_claim(self, claim_id: str) -> Dict[str, Any]:
        owner = self._owning_service(claim_id)
        if owner is not self:
            return owner.get_claim(claim_id)
        record = self._require_claim(claim_id)
        return self._with_live_views(record)

    def get_timeline(self, claim_id: str) -> List[Dict[str, Any]]:
        owner = self._owning_service(claim_id)
        if owner is not self:
            return owner.get_timeline(claim_id)
        self._require_claim(claim_id)
        return [serialize_event(e) for e in self.control_plane.events(claim_id)]

    def get_evidence_request(self, claim_id: str) -> Optional[Dict[str, Any]]:
        owner = self._owning_service(claim_id)
        if owner is not self:
            return owner.get_evidence_request(claim_id)
        record = self._require_claim(claim_id)
        erq = record.get("evidence_request")
        if not erq:
            return None
        erq = dict(erq)
        erq["status"] = derive_evidence_request_status(
            self.control_plane.current_state(claim_id), True
        )
        return erq

    def get_versions(self, claim_id: str) -> Dict[str, Any]:
        owner = self._owning_service(claim_id)
        if owner is not self:
            return owner.get_versions(claim_id)
        record = self._require_claim(claim_id)
        return {
            "claim_id": claim_id,
            "claim_version": record.get("claim_version"),
            "versions": record.get("versions") or [],
            "submissions": record.get("submissions") or [],
        }

    # -- provider consent -----------------------------------------------------

    def record_provider_decision(
        self,
        claim_id: str,
        decision: str,
        reason: Optional[str] = None,
        evidence_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        owner = self._owning_service(claim_id)
        if owner is not self:
            return owner.record_provider_decision(
                claim_id, decision, reason=reason, evidence_ids=evidence_ids
            )
        record = self._require_claim(claim_id)
        erq = record.get("evidence_request") or {}
        persisted = self.control_plane.record_provider_decision(
            claim_id,
            decision,
            claim_version=self.control_plane.current_version(claim_id),
            evidence_ids=evidence_ids,
            evidence_request_id=erq.get("evidence_request_id"),
            correlation_id=erq.get("correlation_id"),
            reason=reason,
        )
        serialized = serialize_provider_decision(persisted)
        self.provider_decision_store.save(serialized)

        from agent2.workflow.control_plane import ClaimWorkflowState
        if self.components is not None and self.control_plane.current_state(claim_id) == ClaimWorkflowState.AWAITING_PROVIDER_DECISION:
            from services.integrated_pipeline import run_agent2_v1_pipeline
            result = run_agent2_v1_pipeline(
                record["canonical_claim"],
                self.components,
                recovery_source=self.recovery_source,
                provider_decision=decision,
                control_plane=self.control_plane,
            )
            new_record = self._serialize_run(record["canonical_claim"], result)
            self._merge_history(record, new_record)
            self.claim_store.save(new_record)
            self._sync_append_only(claim_id)

        return serialized

    def get_provider_decisions(self, claim_id: str) -> List[Dict[str, Any]]:
        owner = self._owning_service(claim_id)
        if owner is not self:
            return owner.get_provider_decisions(claim_id)
        self._require_claim(claim_id)
        return self.provider_decision_store.get(claim_id)

    # -- human review resolution ----------------------------------------------

    def resolve_human_review(
        self,
        claim_id: str,
        resolution_note: str = "",
        attached_evidence: Optional[List[Dict[str, Any]]] = None,
        resolved_by: str = "hospital",
    ) -> Dict[str, Any]:
        owner = self._owning_service(claim_id)
        if owner is not self:
            return owner.resolve_human_review(
                claim_id,
                resolution_note=resolution_note,
                attached_evidence=attached_evidence,
                resolved_by=resolved_by,
            )
        record = self._require_claim(claim_id)
        if record.get("status") == "HUMAN_REVIEW":
            is_verification = bool(record.get("human_verification_pending"))

            if is_verification:
                # Flow A: Agent 1 rejection/escalation. Only Insurance is allowed.
                if str(resolved_by or "").strip().lower() != "insurance":
                    raise PermissionError(
                        "Only the insurance portal may resolve an Agent 1 human review; the "
                        "hospital portal is read-only for Flow A claims."
                    )
            else:
                # Flow B: Agent 2 provider decision. Only Hospital is allowed.
                if str(resolved_by or "").strip().lower() != "hospital":
                    raise PermissionError(
                        "Only the hospital portal may resolve an Agent 2 information request; the "
                        "insurance portal is read-only for Flow B claims."
                    )
        if self.components is None:
            raise RuntimeError("ClaimService components are not configured.")

        from services.integrated_pipeline import reenter_after_human_resolution

        result = reenter_after_human_resolution(
            record["canonical_claim"],
            self.components,
            self.control_plane,
            attached_evidence=attached_evidence or None,
            recovery_source=self.recovery_source,
            resolution_note=resolution_note,
        )
        new_record = self._serialize_run(record["canonical_claim"], result)
        self._merge_history(record, new_record)
        self.claim_store.save(new_record)
        self._sync_append_only(claim_id)
        return self._with_live_views(new_record)

    # -- internals --------------------------------------------------------------

    def _require_claim(self, claim_id: str) -> Dict[str, Any]:
        record = self.claim_store.get(claim_id)
        if record is None:
            raise ClaimNotFound(claim_id)
        return record

    def _canonical_from_request(self, request: CreateClaimRequest) -> Dict[str, Any]:
        if request.canonical_claim:
            canonical = deepcopy(request.canonical_claim)
            if not canonical.get("claim_id"):
                raise ValueError("canonical_claim must carry a claim_id.")
            return canonical

        claim_id = request.claim_id or f"CLM-API-{uuid.uuid4().hex[:8].upper()}"
        metrics: Dict[str, Any] = {"claim_scenario_type": "COMPLETE"}
        if request.payer:
            metrics["claim_payer"] = request.payer
        if request.policy_id:
            metrics["claim_policy_id"] = request.policy_id
        if request.patient_gender:
            metrics["patient_gender"] = request.patient_gender
        if request.procedure:
            # Carry the human-readable procedure description through so API
            # boundaries can display it (display-only; routing ignores it).
            metrics["claim_procedure"] = request.procedure
        metrics.update(request.clinical_metrics)

        return {
            "claim_id": claim_id,
            "patient_id": request.patient_id,
            "submission": {"attempt": 1, "date": request.service_date or _utc_now_iso()},
            "case_data": {
                "case_id": claim_id,
                "patient_age": request.patient_age if request.patient_age is not None else 0,
                "diagnoses": list(request.diagnosis_codes),
                "procedures": [request.procedure_code] if request.procedure_code else [],
                "clinical_metrics": metrics,
            },
            "evidence": deepcopy(request.evidence),
        }

    def _serialize_run(self, canonical: Dict[str, Any], result: Any) -> Dict[str, Any]:
        """Serialize one pipeline run into the stored/API claim record."""
        claim_id = str(canonical.get("claim_id"))
        cp = self.control_plane
        state = cp.current_state(claim_id)
        events = cp.events(claim_id)

        erq = serialize_evidence_request(result.evidence_request)
        if erq:
            erq["status"] = derive_evidence_request_status(state, True)

        submissions = [serialize_submission(s) for s in result.submissions]
        case_metrics = (canonical.get("case_data") or {}).get("clinical_metrics") or {}
        patient_id = (
            canonical.get("patient_id")
            or case_metrics.get("patient_id")
            or case_metrics.get("member_id")
            or "UNKNOWN"
        )

        return {
            "claim_id": claim_id,
            "patient_id": patient_id,
            "status": map_claim_status(state),
            "workflow_state": state.value,
            "claim_version": cp.current_version(claim_id),
            "decision": serialize_decision(result.final_decision),
            "agent2_invoked": result.agent2_invoked,
            "resubmissions": result.resubmissions,
            "human_review_required": result.human_review_required,
            "human_review_reasons": list(result.human_review_reasons),
            # Phase 3 human verification of Agent1 REJECT: pending flag,
            # immutable original rejection snapshot, and the applied human
            # resolution (None until the hospital resolves the hold).
            "human_verification_pending": bool(
                getattr(result, "human_verification_pending", False)
            ),
            "original_rejection": getattr(result, "original_rejection", None),
            "human_resolution": getattr(result, "human_resolution", None),
            "sensitive_blocked": result.sensitive_blocked,
            "provider_declined": result.provider_declined,
            # Phase 1: deterministic prior-auth pre-check outcome recorded on
            # the control plane before Agent 1 (explainable, additive field).
            "prior_auth_precheck": getattr(result, "prior_auth_precheck", None),
            "evidence_request": erq,
            "recovery_result": serialize_recovery_result(result.recovery_result),
            "latest_submission_id": submissions[-1]["submission_id"] if submissions else None,
            "latest_correlation_id": (
                erq["correlation_id"]
                if erq
                else (events[-1].correlation_id if events else None)
            ),
            "versions": [serialize_version(v) for v in result.versions],
            "submissions": submissions,
            "provider_decisions": [
                serialize_provider_decision(d) for d in cp.provider_decisions(claim_id)
            ],
            # Latest canonical snapshot: used for human-resolution re-entry.
            "canonical_claim": canonical,
            "timeline": [serialize_event(e) for e in events],
            "created_at": events[0].timestamp if events else _utc_now_iso(),
            "updated_at": events[-1].timestamp if events else _utc_now_iso(),
        }

    def _merge_history(self, prior: Dict[str, Any], current: Dict[str, Any]) -> None:
        """Keep the full immutable version/submission history across re-entry.

        A re-entry run reports its versions run-locally ("V1", "V2", ...);
        they are relabeled onto the global version series and appended after
        the historical snapshots, which are never overwritten.
        """
        prior_versions = prior.get("versions") or []
        prior_submissions = prior.get("submissions") or []
        offset = len(prior_versions)

        for index, version in enumerate(current.get("versions") or []):
            version["version"] = f"V{offset + index + 1}"
            if index == 0 and offset > 0:
                prior_ev_ids = set(prior_versions[-1].get("evidence_ids") or [])
                curr_ev_ids = set(version.get("evidence_ids") or [])
                new_ids = list(curr_ev_ids - prior_ev_ids)
                if new_ids:
                    version["new_evidence_delta"] = new_ids
        for submission in current.get("submissions") or []:
            label = submission.get("version")
            if isinstance(label, str) and label.startswith("V"):
                try:
                    submission["version"] = f"V{offset + int(label[1:])}"
                    submission["claim_version"] = offset + int(label[1:])
                except ValueError:
                    pass
            if submission.get("submission_id") and submission.get("claim_id") and label:
                submission["submission_id"] = (
                    f"SUB-{submission['claim_id']}-{submission['version']}"
                )

        current["versions"] = prior_versions + (current.get("versions") or [])
        current["submissions"] = prior_submissions + (current.get("submissions") or [])
        if current["submissions"]:
            current["latest_submission_id"] = current["submissions"][-1]["submission_id"]

    def _sync_append_only(self, claim_id: str) -> None:
        """Mirror control-plane append-only artifacts into the repositories.

        Idempotent: provider decisions dedupe by decision_id and events by a
        stable audit_id, so repeated syncs never duplicate history.
        """
        for persisted in self.control_plane.provider_decisions(claim_id):
            self.provider_decision_store.save(serialize_provider_decision(persisted))
        for event in self.control_plane.events(claim_id):
            serialized = serialize_event(event)
            serialized["audit_id"] = f"AUD-{claim_id}-{event.seq}"
            self.event_store.save(serialized)

    def _with_live_views(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Overlay live control-plane views (timeline/decisions) on the snapshot."""
        claim_id = record["claim_id"]
        enriched = dict(record)
        state = self.control_plane.current_state(claim_id)
        enriched["workflow_state"] = state.value
        enriched["status"] = map_claim_status(state)
        enriched["claim_version"] = self.control_plane.current_version(claim_id)
        enriched["timeline"] = [
            serialize_event(e) for e in self.control_plane.events(claim_id)
        ]
        enriched["provider_decisions"] = self.provider_decision_store.get(claim_id)
        if enriched.get("evidence_request"):
            erq = dict(enriched["evidence_request"])
            erq["status"] = derive_evidence_request_status(state, True)
            enriched["evidence_request"] = erq
        return enriched
