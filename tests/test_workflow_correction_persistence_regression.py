"""Workflow-correction persistence regression (cases 7 + 8).

Focused regression over the EXISTING frozen persistence layers:

  Case 7 — refresh/restart preserves exact workflow state and human decision:
    - Flow A (Agent 1 REJECT human verification) and Flow B (Agent 2
      information decision) records survive a fresh service instance over the
      SAME SQLite stores (the production persistence path of api/main.py).
    - The workflow control plane (persist_db=True) reconstructs state,
      events and provider decisions from the agent2 SQLite audit tables.

  Case 8 — Hospital/Insurance views synchronized:
    - Both portal reads of a held Flow B claim are byte-identical on the
      authoritative fields and expose the information-decision purpose
      (human_verification_pending=False), never the Flow A verification flag.

No frozen component is modified; this suite only exercises existing
authoritative paths.
"""

import pytest
from fastapi.testclient import TestClient

from adapters.rag_adapter import CRITERIA_RULES_REGISTRY
from agent2.workflow.control_plane import ClaimWorkflowState, WorkflowControlPlane
from api.claims.service import ClaimService
from api.claims.router import create_claims_app
from tests.test_agent2_v1_end_to_end import (
    _build_components,
    _chunk,
    _ev,
    _pool_source,
    _scenario_claim,
)

PROVIDE_NOTE = "Human review decision: PROVIDE_INFO. Note: LDL report attached."
DENY_NOTE = "Human review decision: REJECT. Note: Hospital cannot provide records."

# Authoritative fields both portals must agree on (same contract as Phase 4).
_SYNC_FIELDS = (
    "claim_id",
    "status",
    "workflow_state",
    "decision",
    "human_verification_pending",
    "human_resolution",
    "original_rejection",
    "agent2_invoked",
    "resubmissions",
    "versions",
    "timeline",
)


@pytest.fixture
def persist_registry(monkeypatch):
    entries = {
        ("POL-PERSIST-LDL", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": {"field": "clinical_metrics.ldl_value", "operator": "lt", "value": 70},
            "evidence_rule": None,
        },
    }
    for key, value in entries.items():
        monkeypatch.setitem(CRITERIA_RULES_REGISTRY, key, value)


@pytest.fixture
def sqlite_stores(monkeypatch, tmp_path):
    """Isolated agent2 SQLite DB + SQLite API repositories (production wiring)."""
    import agent2.database.db_manager as db_manager

    db_file = str(tmp_path / "workflow_persist_regression.db")
    monkeypatch.setattr(db_manager, "DB_PATH", db_file)
    db_manager.init_db()

    from api.persistence.sqlite import (
        SqliteClaimRecordRepository,
        SqliteProviderDecisionRepository,
        SqliteWorkflowEventRepository,
    )

    return {
        "claim_store": SqliteClaimRecordRepository(),
        "provider_decision_store": SqliteProviderDecisionRepository(),
        "event_store": SqliteWorkflowEventRepository(),
    }


def _service_kwargs(components, pool, stores):
    return dict(
        components=components,
        recovery_source=_pool_source(pool),
        control_plane=WorkflowControlPlane(persist_db=True),
        persist_workflow_db=True,
        claim_store=stores["claim_store"],
        provider_decision_store=stores["provider_decision_store"],
        event_store=stores["event_store"],
    )


def _make_client(components, pool, stores):
    service = ClaimService(**_service_kwargs(components, pool, stores))
    return TestClient(create_claims_app(service)), service


def _ldl_chunks():
    return [_chunk("POL-PERSIST-LDL", "C-LDL", "LDL < 70 required")]


# ---------------------------------------------------------------------------
# Case 7 — Flow B resolution survives a full service restart (SQLite)
# ---------------------------------------------------------------------------

class TestFlowBPersistenceAcrossRestart:
    def test_send_information_resolution_survives_restart(self, persist_registry, sqlite_stores):
        components = _build_components(_ldl_chunks())
        pool = [_ev("ldl_report", "EV-PERSIST-1", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]
        client, service = _make_client(components, pool, sqlite_stores)

        # RMI -> Agent 2 recovery -> held for the hospital information decision.
        client.post("/api/claims", json={
            "canonical_claim": _scenario_claim("CLM-WF-P1", "POL-PERSIST-LDL"),
            "provider_decision": "DECLINE",
        })
        held = service.get_claim("CLM-WF-P1")
        assert held["workflow_state"] == "HUMAN_REVIEW"
        assert held["human_verification_pending"] is False  # Flow B purpose

        # Hospital SEND INFORMATION -> exactly one Agent 1 re-evaluation -> APPROVED.
        resolved = client.post(
            "/api/claims/CLM-WF-P1/human-resolution",
            json={
                "resolution_note": PROVIDE_NOTE,
                "attached_evidence": [_ev("ldl_report", "EV-PERSIST-1", {"ldl_value": 55})],
                "resolved_by": "hospital",
            },
        )
        assert resolved.status_code == 200
        assert resolved.json()["workflow_state"] == "APPROVED"
        assert resolved.json()["resubmissions"] == 1

        # Restart: fresh service over the SAME SQLite stores (nothing reverts).
        reloaded = ClaimService(**_service_kwargs(components, pool, sqlite_stores))
        view = reloaded.get_claim("CLM-WF-P1")
        assert view["status"] == "ACCEPTED"
        assert view["workflow_state"] == "APPROVED"
        assert view["claim_version"] == 2
        assert view["resubmissions"] == 1
        assert view["human_verification_pending"] is False
        assert view["decision"]["outcome"] == "APPROVE"
        assert view["human_resolution"] == PROVIDE_NOTE
        # The control plane reconstructs the exact terminal state from SQLite.
        assert reloaded.control_plane.current_state("CLM-WF-P1") == ClaimWorkflowState.APPROVED
        events = reloaded.control_plane.events("CLM-WF-P1")
        states = [e.state_after for e in events]
        assert states[-1] == "APPROVED"
        # Exactly ONE Agent 1 re-evaluation (V2) after the information decision.
        re_eval = [e for e in events if "evaluating V2" in e.action]
        assert len(re_eval) == 1 and re_eval[0].claim_version == 2
        # The hospital information decision itself is persisted in the audit
        # trail (re-entry event detail) and reconstructed after restart.
        assert any(e.detail and "PROVIDE_INFO" in e.detail for e in events)

    def test_deny_information_resolution_survives_restart(self, persist_registry, sqlite_stores):
        components = _build_components(_ldl_chunks())
        pool = [_ev("ldl_report", "EV-PERSIST-2", {"ldl_value": 55})]
        client, service = _make_client(components, pool, sqlite_stores)

        client.post("/api/claims", json={
            "canonical_claim": _scenario_claim("CLM-WF-P2", "POL-PERSIST-LDL"),
            "provider_decision": "DECLINE",
        })
        resolved = client.post(
            "/api/claims/CLM-WF-P2/human-resolution",
            json={"resolution_note": DENY_NOTE, "resolved_by": "hospital"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["workflow_state"] == "REJECTED"

        # Restart: the terminal REJECTED state and the exact human-provided
        # rejection reason are reconstructed from persistence unchanged.
        reloaded = ClaimService(**_service_kwargs(components, pool, sqlite_stores))
        view = reloaded.get_claim("CLM-WF-P2")
        assert view["status"] == "REJECTED"
        assert view["workflow_state"] == "REJECTED"
        assert view["human_resolution"] == DENY_NOTE
        assert "Hospital cannot provide records." in view["decision"]["reasoning"][-1]
        assert reloaded.control_plane.current_state("CLM-WF-P2") == ClaimWorkflowState.REJECTED
        events = reloaded.control_plane.events("CLM-WF-P2")
        assert [e.state_after for e in events][-1] == "REJECTED"
        # The exact human information decision is preserved in the audit trail.
        assert any(e.detail and "Human review decision: REJECT" in e.detail for e in events)

    def test_held_flow_b_state_survives_restart_before_resolution(self, persist_registry, sqlite_stores):
        components = _build_components(_ldl_chunks())
        pool = [_ev("ldl_report", "EV-PERSIST-3", {"ldl_value": 55})]
        client, _ = _make_client(components, pool, sqlite_stores)

        client.post("/api/claims", json={
            "canonical_claim": _scenario_claim("CLM-WF-P3", "POL-PERSIST-LDL"),
            "provider_decision": "DECLINE",
        })

        # Restart while still held: the pending information decision survives.
        reloaded = ClaimService(**_service_kwargs(components, pool, sqlite_stores))
        view = reloaded.get_claim("CLM-WF-P3")
        assert view["workflow_state"] == "HUMAN_REVIEW"
        assert view["human_verification_pending"] is False
        assert view["human_resolution"] is None
        assert view["agent2_invoked"] is True
        assert reloaded.control_plane.current_state("CLM-WF-P3") == ClaimWorkflowState.HUMAN_REVIEW


# ---------------------------------------------------------------------------
# Case 8 — Hospital/Insurance views synchronized on the Flow B hold
# ---------------------------------------------------------------------------

class TestPortalSynchronizationFlowB:
    def test_both_portals_read_identical_information_decision_hold(self, persist_registry, sqlite_stores):
        components = _build_components(_ldl_chunks())
        pool = [_ev("ldl_report", "EV-PERSIST-4", {"ldl_value": 55})]
        client, _ = _make_client(components, pool, sqlite_stores)

        client.post("/api/claims", json={
            "canonical_claim": _scenario_claim("CLM-WF-P4", "POL-PERSIST-LDL"),
            "provider_decision": "DECLINE",
        })

        # Two independent reads of the same authoritative record — the hospital
        # dashboard read and the insurance dashboard read must be identical.
        hospital_view = client.get("/api/claims/CLM-WF-P4").json()
        insurance_view = client.get("/api/claims/CLM-WF-P4").json()
        for field in _SYNC_FIELDS:
            assert hospital_view[field] == insurance_view[field], (
                f"Portal divergence on '{field}'"
            )
        # The hold is the Flow B information decision, never shown as an
        # ordinary Agent 1 rejection verification.
        for view in (hospital_view, insurance_view):
            assert view["workflow_state"] == "HUMAN_REVIEW"
            assert view["human_verification_pending"] is False
            assert view["agent2_invoked"] is True
            assert view["human_resolution"] is None

        # After the hospital resolves, both portals converge on the terminal
        # state with the same decision and timeline (no divergence, no stale
        # HUMAN_REVIEW).
        resolved = client.post(
            "/api/claims/CLM-WF-P4/human-resolution",
            json={
                "resolution_note": PROVIDE_NOTE,
                "attached_evidence": [_ev("ldl_report", "EV-PERSIST-4", {"ldl_value": 55})],
                "resolved_by": "hospital",
            },
        )
        assert resolved.status_code == 200
        hospital_after = client.get("/api/claims/CLM-WF-P4").json()
        insurance_after = client.get("/api/claims/CLM-WF-P4").json()
        for field in _SYNC_FIELDS:
            assert hospital_after[field] == insurance_after[field]
        assert hospital_after["workflow_state"] == "APPROVED"
        # The hospital information decision is preserved in the timeline.
        assert any(
            "PROVIDE_INFO" in str(event.get("detail") or "")
            for event in hospital_after["timeline"]
        )
