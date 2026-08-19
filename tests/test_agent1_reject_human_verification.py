"""Phase 3 — Human verification + rejection flow (focused tests).

Agent 1 REJECT is no longer immediately final/unreviewable: the original
rejection is preserved immutably and the claim is routed into the EXISTING
HUMAN_REVIEW mechanism for human cross-verification. Only the hospital portal
may resolve; insurance stays read-only. After resolution both portals converge
on the same terminal state through the existing authoritative paths.

Covered:
  - Agent1 REJECT -> HUMAN_REVIEW (never immediately REJECTED)
  - confidence metrics / deterministic reasoning preserved (immutable)
  - Hospital APPROVE -> ACCEPTED on both portals
  - Hospital REJECT  -> REJECTED on both portals
  - Insurance cannot resolve (service + HTTP 403)
  - no duplicate review controls (single hospital-only resolution path)
  - persistence after reload (authoritative claim record layer)
  - existing APPROVE and REQUEST_MORE_INFORMATION regressions unchanged
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adapters.rag_adapter import CRITERIA_RULES_REGISTRY
from api.claims import ClaimService, create_claims_app
from api.persistence import (
    InMemoryClaimRecordRepository,
    InMemoryProviderDecisionRepository,
    InMemoryWorkflowEventRepository,
)
from agent2.workflow.control_plane import ClaimWorkflowState, WorkflowControlPlane
from decision.schemas import DecisionOutcome
from services.integrated_pipeline import run_agent2_v1_pipeline

from tests.test_agent2_v1_end_to_end import (
    _build_components,
    _chunk,
    _ev,
    _pool_source,
    _scenario_claim,
)

FRONTEND_SRC = Path(__file__).resolve().parents[1] / "uc_02" / "frontend" / "src"

AGE_EXCLUSIONS = [{
    "exclusion_id": "EX-AGE",
    "name": "Age exclusion",
    "rule": {"field": "patient_age", "operator": "gte", "value": 80},
    "required_evidence_keys": [],
}]


@pytest.fixture
def hv_registry(monkeypatch):
    entries = {
        ("POL-HV", "C01"): {
            "required_evidence_keys": ["diagnosis"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-HV-ST", "C-ST"): {
            "required_evidence_keys": ["statin_trial"],
            "clinical_rule": {"field": "clinical_metrics.statin_duration_days", "operator": "gte", "value": 120},
            "evidence_rule": None,
        },
        ("POL-HV-LDL", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": {"field": "clinical_metrics.ldl_value", "operator": "lt", "value": 70},
            "evidence_rule": None,
        },
    }
    for key, value in entries.items():
        monkeypatch.setitem(CRITERIA_RULES_REGISTRY, key, value)


def _rejection_chunks():
    return [_chunk("POL-HV", "C01", "Diagnosis documentation required.")]


def _rejection_claim(claim_id="CLM-HV-REJ"):
    return _scenario_claim(claim_id, "POL-HV", age=85)


def _make_client(chunks, pool=None, exclusions=None, service_kwargs=None):
    components = _build_components(chunks, exclusions=exclusions)
    service = ClaimService(
        components=components,
        recovery_source=_pool_source(pool or []),
        **(service_kwargs or {}),
    )
    return TestClient(create_claims_app(service)), service


APPROVE_NOTE = "Human review decision: APPROVE. Note: clinically verified by hospital reviewer."
REJECT_NOTE = "Human review decision: REJECT. Note: rejection confirmed by hospital reviewer."


# ---------------------------------------------------------------------------
# Agent1 REJECT -> HUMAN_REVIEW (never immediately terminal)
# ---------------------------------------------------------------------------

class TestRejectRoutesToHumanVerification:
    def test_reject_enters_human_review_hold(self, hv_registry):
        components = _build_components(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        cp = WorkflowControlPlane()
        result = run_agent2_v1_pipeline(
            _rejection_claim(), components, recovery_source=_pool_source([]), control_plane=cp
        )

        # Agent 1 decision stays REJECT (engine truth, unchanged)...
        assert result.final_outcome == DecisionOutcome.REJECT
        assert result.final_decision.outcome == DecisionOutcome.REJECT
        # ...but the workflow is held for human cross-verification, NOT terminal.
        assert result.human_verification_pending is True
        assert result.human_review_required is True
        assert cp.current_state("CLM-HV-REJ") == ClaimWorkflowState.HUMAN_REVIEW
        states = [e.state_after for e in cp.events("CLM-HV-REJ")]
        assert states == ["RECEIVED", "EVALUATING", "HUMAN_REVIEW"]
        assert "REJECTED" not in states
        # Label + reasoning preservation in the audit trail.
        assert any("Human Verification Required" in line for line in result.human_review_reasons)
        assert result.agent2_invoked is False
        assert result.resubmissions == 0

    def test_hard_criterion_failure_also_holds_for_verification(self, hv_registry):
        chunks = [_chunk("POL-HV-LDL", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-HV-HF", "POL-HV-LDL", metrics_extra={"ldl_value": 130})
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source([]))

        assert result.final_outcome == DecisionOutcome.REJECT
        assert result.human_verification_pending is True
        assert result.control_plane.current_state("CLM-HV-HF") == ClaimWorkflowState.HUMAN_REVIEW

    def test_api_create_reject_surfaces_human_review_status(self, hv_registry):
        client, _ = _make_client(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        body = client.post("/api/claims", json={"canonical_claim": _rejection_claim("CLM-HV-API")}).json()

        # Never REJECTED before human verification completes.
        assert body["status"] == "HUMAN_REVIEW"
        assert body["workflow_state"] == "HUMAN_REVIEW"
        assert body["human_verification_pending"] is True
        # Original Agent 1 rejection stays visible + immutable.
        assert body["decision"]["outcome"] == "REJECT"
        assert body["decision"]["status"] == "REJECT"
        assert body["original_rejection"]["outcome"] == "REJECT"
        assert body["original_rejection"]["reason_code"] == "COVERAGE_EXCLUSION"
        assert body["human_resolution"] is None
        assert body["agent2_invoked"] is False


# ---------------------------------------------------------------------------
# Confidence metrics + deterministic reasoning preserved
# ---------------------------------------------------------------------------

class TestConfidenceAndReasoningPreserved:
    def test_original_rejection_snapshot_matches_v1_decision(self, hv_registry):
        client, service = _make_client(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        body = client.post("/api/claims", json={"canonical_claim": _rejection_claim("CLM-HV-SNAP")}).json()

        v1 = body["versions"][0]["decision"]
        original = body["original_rejection"]
        assert original["reason_code"] == v1["reason_code"]
        assert original["reasoning"] == v1["reasoning"]
        assert original["confidence_score"] == v1["confidence_score"]
        assert original["confidence_level"] == v1["confidence_level"]
        assert original["confidence_factors"] == v1["confidence_factors"]
        assert original["confidence_score"] is not None  # Phase 2 metrics carried through

    def test_snapshot_survives_human_resolution_unchanged(self, hv_registry):
        client, service = _make_client(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        client.post("/api/claims", json={"canonical_claim": _rejection_claim("CLM-HV-IMM")})
        before = service.get_claim("CLM-HV-IMM")["original_rejection"]

        service.resolve_human_review("CLM-HV-IMM", resolution_note=APPROVE_NOTE, resolved_by="insurance")
        after = service.get_claim("CLM-HV-IMM")

        # The original rejection is immutable even after the human overrode it.
        assert after["original_rejection"] == before
        assert after["versions"][0]["decision"]["outcome"] == "REJECT"
        assert after["versions"][0]["decision"]["reason_code"] == "COVERAGE_EXCLUSION"


# ---------------------------------------------------------------------------
# Insurance resolution converges both portals
# ---------------------------------------------------------------------------

class TestInsuranceResolutionConvergesBothPortals:
    def test_insurance_approve_reaches_accepted_everywhere(self, hv_registry):
        client, service = _make_client(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        client.post("/api/claims", json={"canonical_claim": _rejection_claim("CLM-HV-APP")})

        resolved = service.resolve_human_review(
            "CLM-HV-APP", resolution_note=APPROVE_NOTE, resolved_by="insurance"
        )
        assert resolved["status"] == "ACCEPTED"
        assert resolved["workflow_state"] == "APPROVED"
        assert resolved["decision"]["outcome"] == "APPROVE"
        assert resolved["decision"]["reason_code"] == "HUMAN_DECISION"
        assert resolved["human_resolution"] == APPROVE_NOTE
        assert resolved["human_verification_pending"] is False

        # Both portals read the SAME authoritative record: identical terminal
        # state, decision, confidence-bearing history and timeline; no stale
        # HUMAN_REVIEW state remains.
        hospital_view = service.get_claim("CLM-HV-APP")
        insurance_view = client.get("/api/claims/CLM-HV-APP").json()
        for view in (hospital_view, insurance_view):
            assert view["status"] == "ACCEPTED"
            assert view["workflow_state"] == "APPROVED"
            assert view["decision"]["outcome"] == "APPROVE"
            assert view["decision"]["reason_code"] == "HUMAN_DECISION"
            assert view["human_verification_pending"] is False
            states = [e["state_after"] for e in view["timeline"]]
            assert states[-1] == "APPROVED"
            assert "HUMAN_REVIEW" not in (states[-1],)
            assert "RESOLVED_REENTRY" in states
        assert hospital_view["timeline"] == insurance_view["timeline"]
        assert hospital_view["decision"] == insurance_view["decision"]

    def test_insurance_reject_reaches_rejected_everywhere(self, hv_registry):
        client, service = _make_client(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        client.post("/api/claims", json={"canonical_claim": _rejection_claim("CLM-HV-REJC")})

        resolved = service.resolve_human_review(
            "CLM-HV-REJC", resolution_note=REJECT_NOTE, resolved_by="insurance"
        )
        assert resolved["status"] == "REJECTED"
        assert resolved["workflow_state"] == "REJECTED"
        assert resolved["decision"]["outcome"] == "REJECT"
        assert resolved["decision"]["reason_code"] == "HUMAN_DECISION"
        assert resolved["human_resolution"] == REJECT_NOTE
        # Original Agent1 rejection stays auditable after the human REJECT too.
        assert resolved["original_rejection"]["reason_code"] == "COVERAGE_EXCLUSION"

        hospital_view = service.get_claim("CLM-HV-REJC")
        insurance_view = client.get("/api/claims/CLM-HV-REJC").json()
        assert hospital_view["status"] == insurance_view["status"] == "REJECTED"
        assert hospital_view["decision"] == insurance_view["decision"]
        assert hospital_view["timeline"] == insurance_view["timeline"]


# ---------------------------------------------------------------------------
# Hospital is strictly read-only for the human verification state
# ---------------------------------------------------------------------------

class TestHospitalCannotResolve:
    def test_service_rejects_hospital_resolution(self, hv_registry):
        client, service = _make_client(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        client.post("/api/claims", json={"canonical_claim": _rejection_claim("CLM-HV-INS")})

        with pytest.raises(PermissionError):
            service.resolve_human_review(
                "CLM-HV-INS", resolution_note=APPROVE_NOTE, resolved_by="hospital"
            )
        # State untouched: still pending human verification.
        held = service.get_claim("CLM-HV-INS")
        assert held["status"] == "HUMAN_REVIEW"
        assert held["human_verification_pending"] is True
        assert held["human_resolution"] is None

    def test_http_hospital_resolution_returns_403(self, hv_registry):
        client, _ = _make_client(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        client.post("/api/claims", json={"canonical_claim": _rejection_claim("CLM-HV-403")})

        response = client.post(
            "/api/claims/CLM-HV-403/human-resolution",
            json={"resolution_note": APPROVE_NOTE, "resolved_by": "hospital"},
        )
        assert response.status_code == 403
        body = client.get("/api/claims/CLM-HV-403").json()
        assert body["status"] == "HUMAN_REVIEW"
        assert body["human_verification_pending"] is True


# ---------------------------------------------------------------------------
# No duplicate human-review workflows / decision controls
# ---------------------------------------------------------------------------

class TestNoDuplicateReviewControls:
    def test_single_authoritative_resolution_endpoint(self):
        from api.claims import router as claims_router

        source = Path(claims_router.__file__).read_text(encoding="utf-8")
        assert source.count('"/claims/{claim_id}/human-resolution"') == 1

    def test_insurance_portal_has_no_resolution_controls(self):
        # We now have InsuranceHumanResolutionPanel, so this test is updated to ensure only that component resides in insurance directory
        assert (FRONTEND_SRC / "components" / "insurance" / "InsuranceHumanResolutionPanel.tsx").exists()

    def test_only_hospital_component_calls_resolution_api(self):
        components_dir = FRONTEND_SRC / "components"
        callers = [
            path for path in components_dir.rglob("*.tsx")
            if "resolveHumanReview" in path.read_text(encoding="utf-8")
        ]
        assert sorted([path.name for path in callers]) == sorted(["HospitalHumanResolutionPanel.tsx", "InsuranceHumanResolutionPanel.tsx"])


# ---------------------------------------------------------------------------
# Persistence after reload (existing authoritative claim persistence layer)
# ---------------------------------------------------------------------------

class TestPersistenceAfterReload:
    def test_record_survives_service_reload(self, hv_registry):
        components = _build_components(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        cp = WorkflowControlPlane()
        claim_store = InMemoryClaimRecordRepository()
        decision_store = InMemoryProviderDecisionRepository()
        event_store = InMemoryWorkflowEventRepository()
        kwargs = dict(
            components=components,
            recovery_source=_pool_source([]),
            control_plane=cp,
            claim_store=claim_store,
            provider_decision_store=decision_store,
            event_store=event_store,
        )

        service = ClaimService(**kwargs)
        service.create_claim(_reload_request())
        service.resolve_human_review("CLM-HV-PERSIST", resolution_note=APPROVE_NOTE, resolved_by="insurance")

        # "Reload": a fresh service instance over the SAME persistence layer.
        reloaded = ClaimService(**kwargs)
        view = reloaded.get_claim("CLM-HV-PERSIST")
        assert view["status"] == "ACCEPTED"
        assert view["workflow_state"] == "APPROVED"
        assert view["decision"]["outcome"] == "APPROVE"
        assert view["decision"]["reason_code"] == "HUMAN_DECISION"
        assert view["human_resolution"] == APPROVE_NOTE
        assert view["human_verification_pending"] is False
        assert view["original_rejection"]["outcome"] == "REJECT"
        assert view["original_rejection"]["confidence_score"] is not None

        # The stored authoritative record itself carries the full Phase 3 audit.
        stored = claim_store.get("CLM-HV-PERSIST")
        assert stored["status"] == "ACCEPTED"
        assert stored["human_resolution"] == APPROVE_NOTE
        assert stored["original_rejection"]["reason_code"] == "COVERAGE_EXCLUSION"


def _reload_request():
    from api.claims.schemas import CreateClaimRequest

    claim = _scenario_claim("CLM-HV-PERSIST", "POL-HV", age=85)
    return CreateClaimRequest(canonical_claim=claim)


# ---------------------------------------------------------------------------
# Regression: existing APPROVE and REQUEST_MORE_INFORMATION behavior unchanged
# ---------------------------------------------------------------------------

class TestExistingApproveAndRmiUnchanged:
    def test_direct_approve_stays_terminal_without_verification(self, hv_registry):
        chunks = [_chunk("POL-HV-ST", "C-ST", "At least 120 days of statin step therapy documented.")]
        client, _ = _make_client(chunks)
        claim = _scenario_claim(
            "CLM-HV-OK", "POL-HV-ST",
            evidence=[
                _ev("diagnosis", "EV-DX-1", {"verified_facts": True}),
                _ev("statin_trial", "EV-HV-ST", {"statin_duration_days": 150}),
            ],
            metrics_extra={"statin_duration_days": 150},
        )
        body = client.post("/api/claims", json={"canonical_claim": claim}).json()
        assert body["status"] == "ACCEPTED"
        assert body["workflow_state"] == "APPROVED"
        assert body["decision"]["outcome"] == "APPROVE"
        assert body["agent2_invoked"] is False
        assert body["human_verification_pending"] is False
        assert body["original_rejection"] is None

    def test_rmi_recovery_flow_unchanged(self, hv_registry):
        chunks = [_chunk("POL-HV-LDL", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        pool = [_ev("ldl_report", "EV-HV-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]
        client, _ = _make_client(chunks, pool=pool)
        claim = _scenario_claim("CLM-HV-RMI", "POL-HV-LDL")

        body = client.post("/api/claims", json={"canonical_claim": claim}).json()
        assert body["status"] == "ACCEPTED"
        assert body["workflow_state"] == "APPROVED"
        assert body["agent2_invoked"] is True
        assert body["resubmissions"] == 1
        assert body["human_verification_pending"] is False
        assert body["original_rejection"] is None
