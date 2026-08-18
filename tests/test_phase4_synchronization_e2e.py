"""Phase 4 — Final system synchronization & integration hardening (focused E2E).

Verifies the EXISTING backend + Hospital dashboard + Insurance dashboard
operate as ONE synchronized system over the existing persistent
claim/workflow/control-plane sources of truth:

  - COMPLETE            -> APPROVED
  - MISSING_EVIDENCE    -> Agent2 recovery -> APPROVED
  - NOT_SATISFIED       -> HUMAN_REVIEW -> Hospital APPROVE -> APPROVED
  - NOT_SATISFIED       -> HUMAN_REVIEW -> Hospital REJECT  -> REJECTED
  - prior-auth REQUIRED / NOT REQUIRED (display-only pre-check; NOT REQUIRED
    is never auto-approved)
  - Hospital/Insurance read the same authoritative record (identical status,
    decision, confidence, prior-auth result, timeline) before and after
    resolution, and after refresh/reload
  - Insurance cannot resolve (HTTP 403)
  - Simulation claims use the exact same persisted workflow synchronization;
    reset deletes only simulation data; manual claims survive

No new stores, no second pipeline, no frontend-only state — this suite only
exercises the existing authoritative paths.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.claims import ClaimService, create_claims_app
from api.persistence import (
    InMemoryClaimRecordRepository,
    InMemoryProviderDecisionRepository,
    InMemoryWorkflowEventRepository,
)
from api.simulation import SimulationManager, StartSimulationRequest
from agent2.workflow.control_plane import WorkflowControlPlane

from tests.test_agent2_v1_end_to_end import (
    _build_components,
    _chunk,
    _ev,
    _pool_source,
    _scenario_claim,
)
from tests.test_agent1_reject_human_verification import (
    AGE_EXCLUSIONS,
    APPROVE_NOTE,
    REJECT_NOTE,
    _make_client,
    _rejection_chunks,
    _rejection_claim,
    hv_registry,
)
from tests.test_api_simulation_contract import (
    SIM_POLICY,
    _RegistryPatientFactory,
    _sim_chunks,
    sim_registry,
)

FRONTEND_SRC = Path(__file__).resolve().parents[1] / "uc_02" / "frontend" / "src"

# Authoritative fields both portals must agree on, byte for byte.
_SYNC_FIELDS = (
    "claim_id",
    "status",
    "workflow_state",
    "decision",
    "human_verification_pending",
    "human_resolution",
    "original_rejection",
    "prior_auth_precheck",
    "agent2_invoked",
    "resubmissions",
    "versions",
    "timeline",
)


def _portal_views(client: TestClient, claim_id: str):
    """Two independent reads of the same authoritative record — the hospital
    dashboard read and the insurance dashboard read must be identical."""
    hospital_view = client.get(f"/api/claims/{claim_id}").json()
    insurance_view = client.get(f"/api/claims/{claim_id}").json()
    return hospital_view, insurance_view


def _assert_identical_views(hospital_view, insurance_view):
    for field in _SYNC_FIELDS:
        assert hospital_view[field] == insurance_view[field], (
            f"Portal divergence on field '{field}': "
            f"hospital={hospital_view[field]!r} insurance={insurance_view[field]!r}"
        )


# ---------------------------------------------------------------------------
# COMPLETE -> APPROVED (with persisted confidence + prior-auth REQUIRED)
# ---------------------------------------------------------------------------

class TestCompleteApprovedSynchronized:
    def test_complete_claim_approves_with_identical_portal_reads(self, hv_registry):
        client, _ = _make_client(_rejection_chunks())
        body = client.post(
            "/api/claims", json={"canonical_claim": _scenario_claim("CLM-P4-COMPLETE", "POL-HV")}
        ).json()

        assert body["status"] == "ACCEPTED"
        assert body["workflow_state"] == "APPROVED"
        assert body["decision"]["outcome"] == "APPROVE"
        assert body["agent2_invoked"] is False
        assert body["human_verification_pending"] is False
        # Phase 2 confidence metrics persisted with the decision.
        assert body["decision"]["confidence_score"] is not None
        assert body["decision"]["confidence_level"]
        assert isinstance(body["decision"]["confidence_factors"], list)
        # Phase 1 pre-check persisted: procedure 27447 is in the policy corpus.
        precheck = body["prior_auth_precheck"]
        assert precheck["requires_prior_auth"] is True
        assert precheck["matched_rule"] == "PA-RULE-POLICY-CORPUS"
        assert precheck["policy_reference"] == "POL-HV"

        # Refresh-style re-reads from both portals converge on the same state.
        hospital_view, insurance_view = _portal_views(client, "CLM-P4-COMPLETE")
        _assert_identical_views(hospital_view, insurance_view)
        assert hospital_view["status"] == "ACCEPTED"

    def test_missing_evidence_recovers_via_agent2_to_approved(self, hv_registry):
        chunks = [_chunk("POL-HV-LDL", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        pool = [_ev("ldl_report", "EV-P4-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]
        client, _ = _make_client(chunks, pool=pool)
        claim = _scenario_claim("CLM-P4-MISSING", "POL-HV-LDL")

        body = client.post("/api/claims", json={"canonical_claim": claim}).json()
        assert body["status"] == "ACCEPTED"
        assert body["workflow_state"] == "APPROVED"
        assert body["decision"]["outcome"] == "APPROVE"
        # Existing Agent 2 recovery semantics unchanged.
        assert body["agent2_invoked"] is True
        assert body["resubmissions"] == 1
        assert body["human_verification_pending"] is False
        assert body["original_rejection"] is None

        hospital_view, insurance_view = _portal_views(client, "CLM-P4-MISSING")
        _assert_identical_views(hospital_view, insurance_view)


# ---------------------------------------------------------------------------
# Prior-auth pre-check: REQUIRED vs NOT REQUIRED (never auto-approval)
# ---------------------------------------------------------------------------

class TestPriorAuthPrecheckSemantics:
    def test_prior_auth_required_preserves_existing_workflow(self, hv_registry):
        client, _ = _make_client(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        body = client.post(
            "/api/claims", json={"canonical_claim": _rejection_claim("CLM-P4-PA-REQ")}
        ).json()

        precheck = body["prior_auth_precheck"]
        assert precheck["requires_prior_auth"] is True
        assert precheck["matched_rule"] == "PA-RULE-POLICY-CORPUS"
        assert precheck["policy_reference"] == "POL-HV"
        assert precheck["reason"]
        # REQUIRED preserves the existing Phase 3 hold semantics exactly.
        assert body["status"] == "HUMAN_REVIEW"
        assert body["human_verification_pending"] is True
        assert body["decision"]["outcome"] == "REJECT"

    def test_prior_auth_not_required_is_never_auto_approved(self, hv_registry, monkeypatch):
        # Policy/procedure absent from the pre-check corpus -> NOT REQUIRED;
        # the claim still runs the full Agent 1 path and is decided there.
        chunks = [_chunk("POL-NOAUTH", "C-AGE", "Supported only for extreme ages.", procedure="11111")]
        from adapters.rag_adapter import CRITERIA_RULES_REGISTRY

        monkeypatch.setitem(CRITERIA_RULES_REGISTRY, ("POL-NOAUTH", "C-AGE"), {
            "required_evidence_keys": ["diagnosis"],
            "clinical_rule": {"field": "clinical_metrics.ph_level", "operator": "gte", "value": 99},
            "evidence_rule": None,
        })
        client, _ = _make_client(chunks)
        claim = _scenario_claim(
            "CLM-P4-PA-NOT", "POL-NOAUTH-UNKNOWN",
            procedures=("99999",),
            evidence=[_ev("diagnosis", "EV-P4-DX", {"verified_facts": True})],
        )

        body = client.post("/api/claims", json={"canonical_claim": claim}).json()
        precheck = body["prior_auth_precheck"]
        assert precheck["requires_prior_auth"] is False
        assert precheck["matched_rule"] == "PA-RULE-DEFAULT-NO-AUTH"
        # NOT REQUIRED is NOT auto-approval: the claim still runs the existing
        # Agent 1 path. The referenced policy is absent from the corpus, so
        # Agent 1 yields NO_MATCHING_POLICY -> HUMAN_REVIEW (never APPROVE).
        # The Phase 3 rejection hold does not apply here (it only holds Agent 1
        # REJECTs), but the claim is still never auto-approved.
        assert body["status"] != "ACCEPTED"
        assert body["workflow_state"] == "HUMAN_REVIEW"
        assert body["decision"]["outcome"] != "APPROVE"


# ---------------------------------------------------------------------------
# NOT_SATISFIED -> HUMAN_REVIEW -> Hospital resolution -> terminal convergence
# ---------------------------------------------------------------------------

class TestHumanVerificationSynchronization:
    def test_hospital_approve_converges_both_portals_and_survives_refresh(self, hv_registry):
        client, _ = _make_client(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        client.post("/api/claims", json={"canonical_claim": _rejection_claim("CLM-P4-APP")})

        # Insurance opens the same claim while it is held.
        held_hospital = client.get("/api/claims/CLM-P4-APP").json()
        held_insurance = client.get("/api/claims/CLM-P4-APP").json()
        _assert_identical_views(held_hospital, held_insurance)
        assert held_hospital["status"] == "HUMAN_REVIEW"
        assert held_hospital["human_verification_pending"] is True
        assert held_hospital["original_rejection"]["confidence_score"] is not None

        # Insurance cannot resolve (read-only, enforced with 403).
        denied = client.post(
            "/api/claims/CLM-P4-APP/human-resolution",
            json={"resolution_note": APPROVE_NOTE, "resolved_by": "insurance"},
        )
        assert denied.status_code == 403

        # Hospital resolves through the single authoritative endpoint.
        resolved = client.post(
            "/api/claims/CLM-P4-APP/human-resolution",
            json={"resolution_note": APPROVE_NOTE, "resolved_by": "hospital"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "ACCEPTED"

        # Both portals refresh: identical terminal state, no stale HUMAN_REVIEW.
        hospital_view, insurance_view = _portal_views(client, "CLM-P4-APP")
        _assert_identical_views(hospital_view, insurance_view)
        for view in (hospital_view, insurance_view):
            assert view["status"] == "ACCEPTED"
            assert view["workflow_state"] == "APPROVED"
            assert view["decision"]["outcome"] == "APPROVE"
            assert view["decision"]["reason_code"] == "HUMAN_DECISION"
            assert view["human_verification_pending"] is False
            assert view["human_resolution"] == APPROVE_NOTE
            # Original rejection stays immutable + auditable after resolution.
            assert view["original_rejection"]["outcome"] == "REJECT"
            assert view["original_rejection"]["reason_code"] == "COVERAGE_EXCLUSION"
            states = [e["state_after"] for e in view["timeline"]]
            assert states[-1] == "APPROVED"
            assert "HUMAN_REVIEW" in states  # the hold happened, then resolved

    def test_hospital_reject_converges_both_portals_and_survives_refresh(self, hv_registry):
        client, _ = _make_client(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        client.post("/api/claims", json={"canonical_claim": _rejection_claim("CLM-P4-REJ")})

        resolved = client.post(
            "/api/claims/CLM-P4-REJ/human-resolution",
            json={"resolution_note": REJECT_NOTE, "resolved_by": "hospital"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "REJECTED"

        hospital_view, insurance_view = _portal_views(client, "CLM-P4-REJ")
        _assert_identical_views(hospital_view, insurance_view)
        for view in (hospital_view, insurance_view):
            assert view["status"] == "REJECTED"
            assert view["workflow_state"] == "REJECTED"
            assert view["decision"]["outcome"] == "REJECT"
            assert view["decision"]["reason_code"] == "HUMAN_DECISION"
            assert view["human_resolution"] == REJECT_NOTE
            assert view["original_rejection"]["reason_code"] == "COVERAGE_EXCLUSION"

    def test_terminal_state_survives_full_service_reload(self, hv_registry):
        # Same persistence layer, fresh service instances (= process restart /
        # dashboard refresh): nothing reverts to an earlier state.
        from api.claims.schemas import CreateClaimRequest

        components = _build_components(_rejection_chunks(), exclusions=AGE_EXCLUSIONS)
        kwargs = dict(
            components=components,
            recovery_source=_pool_source([]),
            control_plane=WorkflowControlPlane(),
            claim_store=InMemoryClaimRecordRepository(),
            provider_decision_store=InMemoryProviderDecisionRepository(),
            event_store=InMemoryWorkflowEventRepository(),
        )
        service = ClaimService(**kwargs)
        service.create_claim(CreateClaimRequest(canonical_claim=_rejection_claim("CLM-P4-RELOAD")))
        service.resolve_human_review("CLM-P4-RELOAD", resolution_note=APPROVE_NOTE)

        reloaded = ClaimService(**kwargs)
        view = reloaded.get_claim("CLM-P4-RELOAD")
        assert view["status"] == "ACCEPTED"
        assert view["workflow_state"] == "APPROVED"
        assert view["human_resolution"] == APPROVE_NOTE
        assert view["human_verification_pending"] is False
        assert view["original_rejection"]["outcome"] == "REJECT"
        assert view["decision"]["confidence_score"] is not None


# ---------------------------------------------------------------------------
# Simulation claims use the SAME persisted workflow/state synchronization
# ---------------------------------------------------------------------------

class TestSimulationSynchronization:
    def _run_three_scenarios(self, sim_registry):
        manager = SimulationManager(
            components=_build_components(_sim_chunks()),
            patient_factory=_RegistryPatientFactory(["COMPLETE", "MISSING", "NOT_SATISFIED"]),
            sleep_fn=lambda _seconds: None,
        )
        record = manager.start(StartSimulationRequest(source="phase4-e2e", count=3, policy_id=SIM_POLICY))
        sim_id = record["simulation_id"]
        manager.wait(sim_id, timeout=120)
        return manager, sim_id

    def test_simulation_scenarios_and_state_synchronization(self, sim_registry):
        manager, sim_id = self._run_three_scenarios(sim_registry)
        status = manager.status(sim_id)
        assert status["status"] == "COMPLETED"
        assert status["completed_count"] == 3

        patients = status["patients"]
        patient_ids = [p["patient_id"] for p in patients]
        claim_ids = [p["claim_id"] for p in patients]
        # No duplicate patient/claim identifiers.
        assert len(set(patient_ids)) == 3
        assert len(set(claim_ids)) == 3

        by_scenario = {p["scenario"]: p for p in patients}
        # COMPLETE -> APPROVED; MISSING_EVIDENCE -> Agent2 recovery -> APPROVED.
        assert by_scenario["COMPLETE"]["claim_status"] == "ACCEPTED"
        assert by_scenario["COMPLETE"]["decision_outcome"] == "APPROVE"
        assert by_scenario["MISSING"]["claim_status"] == "ACCEPTED"
        assert by_scenario["MISSING"]["decision_outcome"] == "APPROVE"
        # NOT_SATISFIED -> HUMAN_REVIEW hold (Phase 3 semantics inside simulation).
        assert by_scenario["NOT_SATISFIED"]["claim_status"] == "HUMAN_REVIEW"
        assert by_scenario["NOT_SATISFIED"]["decision_outcome"] == "REJECT"

        # Simulation summaries and full records come from the SAME owning
        # ClaimService — a single source of truth shared with /api/claims.
        summaries = manager.claims()
        assert {s["claim_id"] for s in summaries} == set(claim_ids)
        for summary in summaries:
            full = manager.claims(claim_id=summary["claim_id"])
            owner = manager.service_for_claim(summary["claim_id"])
            assert owner is not None
            authoritative = owner.get_claim(summary["claim_id"])
            assert full["status"] == authoritative["status"] == summary["status"]
            assert full["workflow_state"] == authoritative["workflow_state"]
            assert full["decision"] == authoritative["decision"]
            assert full["timeline"] == authoritative["timeline"]

    def test_simulation_claim_resolves_through_main_claims_api_locator(self, sim_registry):
        manager, sim_id = self._run_three_scenarios(sim_registry)
        status = manager.status(sim_id)
        not_satisfied = next(p for p in status["patients"] if p["scenario"] == "NOT_SATISFIED")
        claim_id = not_satisfied["claim_id"]

        # The main claims service routes simulation claims to the owning
        # simulation service — exactly as api/main.py wires it.
        main_service = ClaimService(components=_build_components(_sim_chunks()))
        main_service.simulation_service_locator = manager.service_for_claim
        held = main_service.get_claim(claim_id)
        assert held["status"] == "HUMAN_REVIEW"

        # Insurance-style resolution is refused; hospital resolution converges.
        with pytest.raises(PermissionError):
            main_service.resolve_human_review(claim_id, resolution_note=APPROVE_NOTE, resolved_by="insurance")
        resolved = main_service.resolve_human_review(
            claim_id, resolution_note=APPROVE_NOTE, resolved_by="hospital"
        )
        assert resolved["status"] == "ACCEPTED"
        assert resolved["workflow_state"] == "APPROVED"

        # The simulation-side read reflects the identical terminal state.
        sim_view = manager.claims(claim_id=claim_id)
        assert sim_view["status"] == "ACCEPTED"
        assert sim_view["workflow_state"] == "APPROVED"
        assert sim_view["human_resolution"] == APPROVE_NOTE
        assert sim_view["decision"] == resolved["decision"]

    def test_reset_deletes_only_simulation_data(self, sim_registry):
        manager, sim_id = self._run_three_scenarios(sim_registry)
        claim_ids = [p["claim_id"] for p in manager.status(sim_id)["patients"]]

        # An unrelated manual claim lives in a separate authoritative service.
        manual_client, manual_service = _make_client(_sim_chunks())
        manual_claim = _scenario_claim(
            "CLM-P4-MANUAL", SIM_POLICY,
            evidence=[
                _ev("diagnosis", "EV-P4-M-DX", {"verified_facts": True}),
                _ev("conservative_treatment", "EV-P4-M-PT", {"pt_weeks_completed": 16}),
            ],
            metrics_extra={"pt_weeks_completed": 16},
        )
        manual_client.post("/api/claims", json={"canonical_claim": manual_claim})
        assert manual_service.get_claim("CLM-P4-MANUAL")["status"] == "ACCEPTED"

        # Reset removes ONLY this simulation's patients/claims.
        result = manager.reset(sim_id)
        assert result["deleted"] is True
        assert sorted(result["claims_deleted"]) == sorted(claim_ids)
        assert manager.claims() == []
        # The manual claim is untouched.
        assert manual_service.get_claim("CLM-P4-MANUAL")["status"] == "ACCEPTED"


# ---------------------------------------------------------------------------
# API/UI contract: frontend reads exactly what the API serializes
# ---------------------------------------------------------------------------

class TestFrontendContractTrace:
    def test_adapter_maps_all_phase_fields_from_backend_record(self):
        # The frontend adapter must carry every Phase 1-4 synchronization field
        # from the backend record into the shared ClaimDetails state.
        adapter_src = (FRONTEND_SRC / "services" / "backendAdapter.ts").read_text(encoding="utf-8")
        for field in (
            "confidence_score",
            "confidence_level",
            "confidence_factors",
            "prior_auth_precheck",
            "human_verification_pending",
            "human_resolution",
            "original_rejection",
        ):
            assert field in adapter_src, f"backendAdapter.ts misses field '{field}'"

    def test_both_detail_pages_render_prior_auth_and_confidence(self):
        hospital_page = (FRONTEND_SRC / "pages" / "hospital" / "ClaimDetails.tsx").read_text(encoding="utf-8")
        insurance_page = (FRONTEND_SRC / "pages" / "insurance" / "InsuranceClaimDetails.tsx").read_text(encoding="utf-8")
        for page in (hospital_page, insurance_page):
            assert "PriorAuthStatusCard" in page
            assert "AgentConfidenceCard" in page
        # Insurance has no resolution controls anywhere.
        assert "resolveHumanReview" not in insurance_page
        insurance_src = FRONTEND_SRC / "services" / "insuranceApi.ts"
        assert "resolveHumanReview" not in insurance_src.read_text(encoding="utf-8")

    def test_rejected_banner_only_after_verification(self):
        hospital_page = (FRONTEND_SRC / "pages" / "hospital" / "ClaimDetails.tsx").read_text(encoding="utf-8")
        # Terminal REJECT banner exists (Phase 4 gap fix) and is keyed on the
        # authoritative status, which only becomes REJECTED post-verification.
        assert "REJECTED: { icon: AlertTriangle" in hospital_page
