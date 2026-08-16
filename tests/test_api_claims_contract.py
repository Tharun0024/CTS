"""Phase 5A — API + persistence contract tests.

Verifies the stable API boundary over the existing V1 workflow:
  - create/list/get claims, status + decision
  - workflow timeline, evidence request/status
  - provider evidence accept/decline
  - resubmission/version history
  - HUMAN_REVIEW + human resolution (re-entry through normal Agent1 routing)
  - frozen routing preserved (APPROVE/REJECT terminal, RMI -> Agent2)
  - patient_id, claim_version, submission_id, evidence_request_id,
    correlation_id consistency
  - repository interfaces (in-memory and SQLite are interchangeable)

All tests run fully offline using the same mocked RAG/LLM components as
tests/test_agent2_v1_end_to_end.py.
"""

import pytest
from fastapi.testclient import TestClient

from adapters.rag_adapter import CRITERIA_RULES_REGISTRY
from api.claims import ClaimService, create_claims_app
from api.claims.mapping import (
    DECISION_TO_FRONTEND,
    WORKFLOW_STATE_TO_CLAIM_STATUS,
    derive_evidence_request_status,
    map_claim_status,
    map_decision_status,
)
from agent2.workflow.control_plane import ClaimWorkflowState
from decision.schemas import DecisionOutcome

from tests.test_agent2_v1_end_to_end import (
    _build_components,
    _chunk,
    _ev,
    _pool_source,
    _scenario_claim,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def api_registry(monkeypatch):
    entries = {
        ("POL-API-LDL", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": {"field": "clinical_metrics.ldl_value", "operator": "lt", "value": 70},
            "evidence_rule": None,
        },
        ("POL-API-ST", "C-ST"): {
            "required_evidence_keys": ["statin_trial"],
            "clinical_rule": {"field": "clinical_metrics.statin_duration_days", "operator": "gte", "value": 120},
            "evidence_rule": None,
        },
        ("POL-API-MET", "C-MET"): {
            "required_evidence_keys": ["metformin_trial"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-API-EX", "C01"): {
            "required_evidence_keys": ["diagnosis"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
    }
    for key, value in entries.items():
        monkeypatch.setitem(CRITERIA_RULES_REGISTRY, key, value)


AGE_EXCLUSIONS = [{
    "exclusion_id": "EX-AGE",
    "name": "Age exclusion",
    "rule": {"field": "patient_age", "operator": "gte", "value": 80},
    "required_evidence_keys": [],
}]


def _make_client(chunks, pool, exclusions=None, service_kwargs=None):
    """Build a TestClient over the claims API with mocked pipeline components."""
    components = _build_components(chunks, exclusions=exclusions)
    service = ClaimService(
        components=components,
        recovery_source=_pool_source(pool),
        **(service_kwargs or {}),
    )
    return TestClient(create_claims_app(service)), service


def _ldl_chunks():
    return [_chunk("POL-API-LDL", "C-LDL", "Documented LDL cholesterol level below 70 mg/dL required.")]


def _ldl_pool():
    return [_ev("ldl_report", "EV-API-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]


# ---------------------------------------------------------------------------
# Enum/status mapping contract
# ---------------------------------------------------------------------------

class TestEnumMappingContract:
    def test_decision_outcomes_map_to_frontend_statuses(self):
        assert map_decision_status(DecisionOutcome.APPROVE) == "ACCEPT"
        assert map_decision_status(DecisionOutcome.REJECT) == "REJECT"
        assert map_decision_status(DecisionOutcome.REQUEST_MORE_INFORMATION) == "MORE_INFORMATION"
        assert map_decision_status(DecisionOutcome.HUMAN_REVIEW) == "HUMAN_REVIEW"
        # Backend enums themselves remain untouched (frozen semantics).
        assert DecisionOutcome.APPROVE.value == "APPROVE"
        assert DecisionOutcome.REQUEST_MORE_INFORMATION.value == "REQUEST_MORE_INFORMATION"

    def test_workflow_states_map_to_claim_statuses(self):
        assert map_claim_status(ClaimWorkflowState.APPROVED) == "ACCEPTED"
        assert map_claim_status(ClaimWorkflowState.REJECTED) == "REJECTED"
        assert map_claim_status(ClaimWorkflowState.HUMAN_REVIEW) == "HUMAN_REVIEW"
        assert map_claim_status(ClaimWorkflowState.RECOVERING) == "UNDER_REVIEW"
        assert map_claim_status(ClaimWorkflowState.AWAITING_PROVIDER_DECISION) == "MORE_INFO"
        assert map_claim_status(ClaimWorkflowState.RESUBMITTING) == "SUBMITTED_AGAIN"
        assert map_claim_status(ClaimWorkflowState.RECEIVED) == "SUBMITTED"
        assert map_claim_status(ClaimWorkflowState.EVALUATING) == "PROCESSING"
        # Fail-closed system failures never surface as approval.
        assert map_claim_status(ClaimWorkflowState.FAILED) == "HUMAN_REVIEW"
        # Every legal state has a mapping (no gaps).
        assert set(WORKFLOW_STATE_TO_CLAIM_STATUS) == set(ClaimWorkflowState)
        assert set(DECISION_TO_FRONTEND) == set(DecisionOutcome)

    def test_evidence_request_status_derivation(self):
        S = ClaimWorkflowState
        assert derive_evidence_request_status(S.RECOVERING, False) == "CLOSED"
        assert derive_evidence_request_status(S.ROUTED_RECOVERY, True) == "PENDING_PROVIDER_RESPONSE"
        assert derive_evidence_request_status(S.RECOVERING, True) == "PENDING_PROVIDER_RESPONSE"
        assert derive_evidence_request_status(S.AWAITING_PROVIDER_DECISION, True) == "WAITING_FOR_PROVIDER"
        assert derive_evidence_request_status(S.RESUBMITTING, True) == "RECEIVED"
        assert derive_evidence_request_status(S.APPROVED, True) == "CLOSED"
        assert derive_evidence_request_status(S.HUMAN_REVIEW, True) == "CLOSED"


# ---------------------------------------------------------------------------
# Create / list / get + frozen routing through the API
# ---------------------------------------------------------------------------

class TestCreateAndRetrieve:
    def test_rmi_recovery_approve_full_contract(self, api_registry):
        client, _ = _make_client(_ldl_chunks(), _ldl_pool())
        claim = _scenario_claim("CLM-API-RMI", "POL-API-LDL")

        created = client.post("/api/claims", json={"canonical_claim": claim})
        assert created.status_code == 201
        body = created.json()

        # Identity + mapping
        assert body["claim_id"] == "CLM-API-RMI"
        assert body["patient_id"] == "PA-TEST"               # patient_id preserved
        assert body["status"] == "ACCEPTED"                   # APPROVE -> ACCEPTED
        assert body["workflow_state"] == "APPROVED"
        assert body["decision"]["outcome"] == "APPROVE"       # backend truth kept
        assert body["decision"]["status"] == "ACCEPT"         # frontend contract
        # Agent2 recovery ran exactly once (frozen RMI route)
        assert body["agent2_invoked"] is True
        assert body["resubmissions"] == 1
        assert body["claim_version"] == 2
        # Evidence request identity
        erq = body["evidence_request"]
        assert erq["evidence_request_id"].startswith("ERQ-")
        assert erq["correlation_id"] == "CORR-CLM-API-RMI-V1"
        assert erq["claim_version"] == 1
        # Submission identity
        assert body["latest_submission_id"].startswith("SUB-")
        assert body["latest_correlation_id"] == erq["correlation_id"]

        # List endpoint
        listing = client.get("/api/claims").json()
        assert len(listing) == 1
        assert listing[0]["claim_id"] == "CLM-API-RMI"
        assert listing[0]["status"] == "ACCEPTED"
        assert listing[0]["decision_status"] == "ACCEPT"

        # Get endpoint matches creation response on all contract fields
        detail = client.get("/api/claims/CLM-API-RMI").json()
        for key in ("claim_id", "patient_id", "status", "workflow_state",
                    "claim_version", "decision", "evidence_request",
                    "latest_submission_id", "agent2_invoked", "resubmissions"):
            assert detail[key] == body[key]

    def test_direct_approve_is_terminal_without_agent2(self, api_registry):
        chunks = [_chunk("POL-API-ST", "C-ST", "At least 120 days of statin step therapy documented.")]
        client, _ = _make_client(chunks, pool=[])
        claim = _scenario_claim(
            "CLM-API-APP", "POL-API-ST",
            evidence=[
                _ev("diagnosis", "EV-DX-1", {"verified_facts": True}),
                _ev("statin_trial", "EV-API-ST-OK", {"statin_duration_days": 150}),
            ],
            metrics_extra={"statin_duration_days": 150},
        )

        body = client.post("/api/claims", json={"canonical_claim": claim}).json()
        assert body["status"] == "ACCEPTED"
        assert body["decision"]["outcome"] == "APPROVE"
        assert body["agent2_invoked"] is False
        assert body["evidence_request"] is None
        assert body["claim_version"] == 1
        assert len(body["versions"]) == 1
        assert body["submissions"] == []

    def test_hard_reject_is_terminal_without_agent2(self, api_registry):
        chunks = [_chunk("POL-API-EX", "C01", "Diagnosis documentation required.")]
        client, _ = _make_client(chunks, pool=_ldl_pool(), exclusions=AGE_EXCLUSIONS)
        claim = _scenario_claim("CLM-API-REJ", "POL-API-EX", age=85)

        body = client.post("/api/claims", json={"canonical_claim": claim}).json()
        assert body["status"] == "REJECTED"
        assert body["workflow_state"] == "REJECTED"
        assert body["decision"]["outcome"] == "REJECT"
        assert body["decision"]["status"] == "REJECT"
        assert body["agent2_invoked"] is False               # frozen: REJECT never recovers
        assert body["evidence_request"] is None
        assert len(body["versions"]) == 1
        assert body["submissions"] == []

    def test_unknown_claim_returns_404(self, api_registry):
        client, _ = _make_client(_ldl_chunks(), _ldl_pool())
        assert client.get("/api/claims/NOPE").status_code == 404
        assert client.get("/api/claims/NOPE/timeline").status_code == 404
        assert client.get("/api/claims/NOPE/evidence-request").status_code == 404
        assert client.get("/api/claims/NOPE/versions").status_code == 404
        assert client.get("/api/claims/NOPE/provider-decisions").status_code == 404
        assert client.post("/api/claims/NOPE/provider-decision",
                           json={"decision": "ACCEPT"}).status_code == 404
        assert client.post("/api/claims/NOPE/human-resolution",
                           json={}).status_code == 404

    def test_terminal_claim_cannot_be_reprocessed(self, api_registry):
        """Re-creating the same claim_id violates the frozen terminal state."""
        client, _ = _make_client(_ldl_chunks(), _ldl_pool())
        claim = _scenario_claim("CLM-API-DUP", "POL-API-LDL")
        assert client.post("/api/claims", json={"canonical_claim": claim}).status_code == 201
        blocked = client.post("/api/claims", json={"canonical_claim": claim})
        assert blocked.status_code == 409

    def test_structured_fields_build_canonical_claim(self, api_registry):
        """Frontend-style CreateClaimPayload (no canonical passthrough)."""
        chunks = [_chunk("POL-API-MET", "C-MET", "Documented metformin trial required.")]
        client, _ = _make_client(chunks, pool=[])  # nothing recoverable
        payload = {
            "claim_id": "CLM-API-FE",
            "patient_id": "PA-FRONTEND",
            "patient_age": 61,
            "payer": "Aetna",
            "policy_id": "POL-API-MET",
            "procedure_code": "27447",
            "procedure": "Knee Replacement",
            "diagnosis_codes": ["M17.11"],
            "service_date": "2026-08-16",
            "evidence": [_ev("diagnosis", "EV-FE-DX", {"verified_facts": True})],
        }
        created = client.post("/api/claims", json=payload)
        assert created.status_code == 201
        body = created.json()
        assert body["claim_id"] == "CLM-API-FE"
        assert body["patient_id"] == "PA-FRONTEND"
        # RMI -> recovery found nothing -> HUMAN_REVIEW (no fabrication).
        assert body["status"] == "HUMAN_REVIEW"
        # Agent1's immutable decision stays RMI; the HUMAN_REVIEW escalation is
        # a workflow-level outcome (no recoverable evidence exists).
        assert body["decision"]["outcome"] == "REQUEST_MORE_INFORMATION"
        assert body["decision"]["status"] == "MORE_INFORMATION"
        assert body["human_review_required"] is True


# ---------------------------------------------------------------------------
# Timeline + evidence request endpoints
# ---------------------------------------------------------------------------

class TestTimelineAndEvidenceRequest:
    @pytest.fixture
    def rmi_client(self, api_registry):
        client, service = _make_client(_ldl_chunks(), _ldl_pool())
        claim = _scenario_claim("CLM-API-TL", "POL-API-LDL")
        client.post("/api/claims", json={"canonical_claim": claim})
        return client

    def test_timeline_covers_full_lifecycle(self, rmi_client):
        body = rmi_client.get("/api/claims/CLM-API-TL/timeline").json()
        events = body["events"]
        assert body["claim_id"] == "CLM-API-TL"
        states = [e["state_after"] for e in events]
        assert states[0] == "RECEIVED"
        assert states[-1] == "APPROVED"
        # Frozen recovery path is present in order.
        for expected in ("EVALUATING", "ROUTED_RECOVERY", "RECOVERING",
                         "AWAITING_PROVIDER_DECISION", "RESUBMITTING"):
            assert expected in states
        assert states.index("ROUTED_RECOVERY") < states.index("RECOVERING")
        # Immutable ordering: strictly increasing seq.
        seqs = [e["seq"] for e in events]
        assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)

    def test_timeline_carries_correlation_and_request_ids(self, rmi_client):
        detail = rmi_client.get("/api/claims/CLM-API-TL").json()
        erq = detail["evidence_request"]
        events = rmi_client.get("/api/claims/CLM-API-TL/timeline").json()["events"]

        routed = [e for e in events if e["state_after"] == "ROUTED_RECOVERY"][0]
        assert routed["correlation_id"] == erq["correlation_id"]
        recovering = [e for e in events if e["state_after"] == "RECOVERING"][0]
        assert recovering["evidence_request_id"] == erq["evidence_request_id"]
        assert recovering["correlation_id"] == erq["correlation_id"]
        # Re-evaluation event tracks the new claim version.
        eval_events = [e for e in events if e["state_after"] == "EVALUATING"]
        assert eval_events[-1]["claim_version"] == 2

    def test_evidence_request_endpoint(self, rmi_client):
        body = rmi_client.get("/api/claims/CLM-API-TL/evidence-request").json()
        erq = body["evidence_request"]
        assert body["claim_id"] == "CLM-API-TL"
        assert erq["evidence_request_id"].startswith("ERQ-")
        assert erq["correlation_id"] == "CORR-CLM-API-TL-V1"
        assert erq["claim_version"] == 1
        assert erq["patient_id"] == "PA-TEST"
        assert erq["requested_information"] or erq["evidence_keys"] or erq["criterion_ids"]
        # Completed run: request lifecycle is closed.
        assert erq["status"] == "CLOSED"

    def test_evidence_request_absent_for_terminal_reject(self, api_registry):
        chunks = [_chunk("POL-API-EX", "C01", "Diagnosis documentation required.")]
        client, _ = _make_client(chunks, pool=[], exclusions=AGE_EXCLUSIONS)
        claim = _scenario_claim("CLM-API-TLR", "POL-API-EX", age=85)
        client.post("/api/claims", json={"canonical_claim": claim})
        body = client.get("/api/claims/CLM-API-TLR/evidence-request").json()
        assert body["evidence_request"] is None


# ---------------------------------------------------------------------------
# Version / submission history
# ---------------------------------------------------------------------------

class TestVersionHistory:
    def test_versions_and_submissions_are_immutable_and_linked(self, api_registry):
        client, _ = _make_client(_ldl_chunks(), _ldl_pool())
        claim = _scenario_claim("CLM-API-VH", "POL-API-LDL")
        client.post("/api/claims", json={"canonical_claim": claim})

        body = client.get("/api/claims/CLM-API-VH/versions").json()
        assert body["claim_id"] == "CLM-API-VH"
        assert body["claim_version"] == 2
        versions = body["versions"]
        assert [v["version"] for v in versions] == ["V1", "V2"]
        # V1 history preserved immutably: RMI without recovered evidence.
        assert versions[0]["decision"]["outcome"] == "REQUEST_MORE_INFORMATION"
        assert versions[0]["decision"]["status"] == "MORE_INFORMATION"
        assert versions[0]["new_evidence_delta"] == []
        assert versions[0]["evidence_ids"] == ["EV-DX-1"]
        # V2 carries exactly the recovered record.
        assert versions[1]["decision"]["status"] == "ACCEPT"
        assert versions[1]["new_evidence_delta"] == ["EV-API-LDL"]
        assert versions[1]["evidence_ids"] == ["EV-DX-1", "EV-API-LDL"]

        submissions = body["submissions"]
        assert len(submissions) == 1
        sub = submissions[0]
        assert sub["submission_id"].startswith("SUB-")
        assert sub["claim_id"] == "CLM-API-VH"
        assert sub["claim_version"] == 2
        assert sub["correlation_id"] == "CORR-CLM-API-VH-V1"
        assert sub["evidence_request_id"].startswith("ERQ-")
        assert sub["new_evidence_delta"] == ["EV-API-LDL"]

    def test_terminal_reject_has_single_version_no_submissions(self, api_registry):
        chunks = [_chunk("POL-API-EX", "C01", "Diagnosis documentation required.")]
        client, _ = _make_client(chunks, pool=[], exclusions=AGE_EXCLUSIONS)
        claim = _scenario_claim("CLM-API-VHR", "POL-API-EX", age=85)
        client.post("/api/claims", json={"canonical_claim": claim})

        body = client.get("/api/claims/CLM-API-VHR/versions").json()
        assert body["claim_version"] == 1
        assert len(body["versions"]) == 1
        assert body["submissions"] == []


# ---------------------------------------------------------------------------
# Provider evidence accept/decline
# ---------------------------------------------------------------------------

class TestProviderDecisions:
    @pytest.fixture
    def rmi_client(self, api_registry):
        client, service = _make_client(_ldl_chunks(), _ldl_pool())
        claim = _scenario_claim("CLM-API-PD", "POL-API-LDL")
        client.post("/api/claims", json={"canonical_claim": claim})
        return client

    def test_pipeline_recorded_accept_is_visible(self, rmi_client):
        body = rmi_client.get("/api/claims/CLM-API-PD/provider-decisions").json()
        decisions = body["provider_decisions"]
        assert len(decisions) == 1
        rec = decisions[0]
        assert rec["decision"] == "ACCEPT"
        assert rec["decision_id"].startswith("PRV-")
        assert rec["evidence_ids"] == ["EV-API-LDL"]
        assert rec["correlation_id"] == "CORR-CLM-API-PD-V1"
        assert rec["evidence_request_id"].startswith("ERQ-")

    def test_extra_decision_appends_never_overwrites(self, rmi_client):
        posted = rmi_client.post(
            "/api/claims/CLM-API-PD/provider-decision",
            json={"decision": "DECLINE", "reason": "Provider audit drill",
                  "evidence_ids": ["EV-API-LDL"]},
        )
        assert posted.status_code == 201
        rec = posted.json()
        assert rec["decision"] == "DECLINE"
        assert rec["claim_id"] == "CLM-API-PD"
        assert rec["correlation_id"] == "CORR-CLM-API-PD-V1"

        history = rmi_client.get("/api/claims/CLM-API-PD/provider-decisions").json()
        decisions = history["provider_decisions"]
        assert [d["decision"] for d in decisions] == ["ACCEPT", "DECLINE"]
        assert len({d["decision_id"] for d in decisions}) == 2  # distinct records

    def test_invalid_provider_decision_rejected(self, rmi_client):
        # Pydantic literal blocks anything but ACCEPT/DECLINE.
        bad = rmi_client.post("/api/claims/CLM-API-PD/provider-decision",
                              json={"decision": "MAYBE"})
        assert bad.status_code == 422


# ---------------------------------------------------------------------------
# HUMAN_REVIEW lifecycle + human resolution
# ---------------------------------------------------------------------------

class TestHumanReviewLifecycle:
    @pytest.fixture
    def hr_client(self, api_registry):
        chunks = [_chunk("POL-API-MET", "C-MET", "Documented metformin trial required.")]
        client, service = _make_client(chunks, pool=[])  # nothing recoverable
        claim = _scenario_claim("CLM-API-HR", "POL-API-MET")
        created = client.post("/api/claims", json={"canonical_claim": claim}).json()
        assert created["status"] == "HUMAN_REVIEW"
        assert created["agent2_invoked"] is True  # recovery attempted, all MISSING
        return client

    def test_resolution_without_evidence_repeats_deterministically(self, hr_client):
        resolved = hr_client.post(
            "/api/claims/CLM-API-HR/human-resolution",
            json={"resolution_note": "No additional records available."},
        )
        assert resolved.status_code == 200
        body = resolved.json()
        # Re-entered NORMAL routing: still missing -> HUMAN_REVIEW again.
        assert body["status"] == "HUMAN_REVIEW"
        # Timeline shows the legal exit: RESOLVED_REENTRY -> RECEIVED.
        states = [e["state_after"] for e in body["timeline"]]
        assert "RESOLVED_REENTRY" in states
        assert states[states.index("RESOLVED_REENTRY") + 1] == "RECEIVED"
        # No fabricated V2 evidence was created.
        assert body["versions"][0]["evidence_ids"] == ["EV-DX-1"]

    def test_resolution_with_real_evidence_reenters_and_approves(self, hr_client):
        resolved = hr_client.post(
            "/api/claims/CLM-API-HR/human-resolution",
            json={
                "resolution_note": "Metformin trial record located.",
                "attached_evidence": [
                    _ev("metformin_trial", "EV-API-HUMAN", {"verified_facts": True}),
                ],
            },
        )
        assert resolved.status_code == 200
        body = resolved.json()
        assert body["status"] == "ACCEPTED"
        assert body["decision"]["outcome"] == "APPROVE"
        # The human-attached real record entered the newest version only.
        latest = body["versions"][-1]
        assert "EV-API-HUMAN" in latest["evidence_ids"]
        assert "EV-API-HUMAN" not in body["versions"][0]["evidence_ids"]

    def test_resolution_on_non_review_claim_is_conflict(self, hr_client, api_registry):
        # Terminal claim: human resolution is illegal (409).
        client2, _ = _make_client(_ldl_chunks(), _ldl_pool())
        claim = _scenario_claim("CLM-API-HR2", "POL-API-LDL")
        client2.post("/api/claims", json={"canonical_claim": claim})
        blocked = client2.post("/api/claims/CLM-API-HR2/human-resolution", json={})
        assert blocked.status_code == 409

    def test_fabricated_attachment_rejected(self, hr_client):
        bad = hr_client.post(
            "/api/claims/CLM-API-HR/human-resolution",
            json={"attached_evidence": [{"extracted_facts": {"made_up": True}}]},
        )
        assert bad.status_code == 422


# ---------------------------------------------------------------------------
# Repository interfaces: in-memory <-> SQLite interchangeability
# ---------------------------------------------------------------------------

class TestRepositoryInterfaces:
    def test_sqlite_stores_satisfy_same_contract(self, api_registry, monkeypatch, tmp_path):
        import agent2.database.db_manager as db_manager

        db_file = str(tmp_path / "phase5a_api.db")
        monkeypatch.setattr(db_manager, "DB_PATH", db_file)

        from api.persistence.sqlite import (
            SqliteClaimRecordRepository,
            SqliteProviderDecisionRepository,
            SqliteWorkflowEventRepository,
        )

        claim_store = SqliteClaimRecordRepository()
        decision_store = SqliteProviderDecisionRepository()
        event_store = SqliteWorkflowEventRepository()
        client, service = _make_client(
            _ldl_chunks(), _ldl_pool(),
            service_kwargs={
                "claim_store": claim_store,
                "provider_decision_store": decision_store,
                "event_store": event_store,
            },
        )
        claim = _scenario_claim("CLM-API-DB", "POL-API-LDL")
        created = client.post("/api/claims", json={"canonical_claim": claim})
        assert created.status_code == 201

        # Claim record persisted to SQLite and reloadable.
        stored = claim_store.get("CLM-API-DB")
        assert stored is not None
        assert stored["status"] == "ACCEPTED"
        assert stored["patient_id"] == "PA-TEST"
        assert stored["claim_version"] == 2
        assert [r["claim_id"] for r in claim_store.list()] == ["CLM-API-DB"]

        # Provider decision history persisted (pipeline-recorded ACCEPT).
        decisions = decision_store.get("CLM-API-DB")
        assert [d["decision"] for d in decisions] == ["ACCEPT"]
        assert decisions[0]["correlation_id"] == "CORR-CLM-API-DB-V1"
        assert decisions[0]["evidence_request_id"].startswith("ERQ-")

        # Workflow events mirrored; re-sync is idempotent (append-only safe).
        events = event_store.get_events("CLM-API-DB")
        assert [e["state_after"] for e in events][0] == "RECEIVED"
        assert [e["state_after"] for e in events][-1] == "APPROVED"
        service._sync_append_only("CLM-API-DB")
        assert len(event_store.get_events("CLM-API-DB")) == len(events)
        assert len(decision_store.get("CLM-API-DB")) == len(decisions)

        # A fresh service over the same SQLite stores sees the same claims.
        assert claim_store.get("CLM-API-DB")["claim_id"] == "CLM-API-DB"

    def test_in_memory_stores_roundtrip_and_append_only(self):
        from api.persistence import (
            InMemoryClaimRecordRepository,
            InMemoryProviderDecisionRepository,
            InMemoryWorkflowEventRepository,
        )

        claims = InMemoryClaimRecordRepository()
        claims.save({"claim_id": "C1", "status": "ACCEPTED", "updated_at": "2"})
        claims.save({"claim_id": "C1", "status": "REJECTED", "updated_at": "3"})  # upsert
        claims.save({"claim_id": "C0", "status": "DRAFT", "updated_at": "1"})
        assert claims.get("C1")["status"] == "REJECTED"
        assert [r["claim_id"] for r in claims.list()] == ["C1", "C0"]
        with pytest.raises(ValueError):
            claims.save({"status": "DRAFT"})

        decisions = InMemoryProviderDecisionRepository()
        decisions.save({"decision_id": "PRV-1", "claim_id": "C1", "decision": "ACCEPT"})
        decisions.save({"decision_id": "PRV-1", "claim_id": "C1", "decision": "ACCEPT"})
        assert len(decisions.get("C1")) == 1  # idempotent by decision_id

        events = InMemoryWorkflowEventRepository()
        events.save({"claim_id": "C1", "seq": 1})
        events.save({"claim_id": "C1", "seq": 2})
        assert [e["seq"] for e in events.get_events("C1")] == [1, 2]
