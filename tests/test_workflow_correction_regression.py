import pytest
from fastapi.testclient import TestClient
from adapters.rag_adapter import CRITERIA_RULES_REGISTRY
from decision.schemas import DecisionOutcome
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

@pytest.fixture
def workflow_registry(monkeypatch):
    entries = {
        ("POL-REG-LDL", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": {"field": "clinical_metrics.ldl_value", "operator": "lt", "value": 70},
            "evidence_rule": None,
        },
        ("POL-REG-MET", "C-MET"): {
            "required_evidence_keys": ["metformin_trial"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
    }
    for key, value in entries.items():
        monkeypatch.setitem(CRITERIA_RULES_REGISTRY, key, value)


def _make_test_client(chunks, pool, exclusions=None):
    components = _build_components(chunks, exclusions=exclusions)
    control_plane = WorkflowControlPlane()
    service = ClaimService(
        components=components,
        recovery_source=_pool_source(pool),
        control_plane=control_plane,
    )
    return TestClient(create_claims_app(service)), service


# ---------------------------------------------------------------------------
# Flow A scenarios
# ---------------------------------------------------------------------------

def test_flow_a_rejection_resolution(workflow_registry):
    chunks = [_chunk("POL-REG-LDL", "C-LDL", "LDL < 70 required")]
    claim = _scenario_claim("CLM-FLA-1", "POL-REG-LDL", metrics_extra={"ldl_value": 130})
    client, _ = _make_test_client(chunks, pool=[])

    # 1. Agent 1 REJECT -> Insurance HUMAN_REVIEW (human_verification_pending = True)
    created = client.post("/api/claims", json={"canonical_claim": claim}).json()
    assert created["workflow_state"] == "HUMAN_REVIEW"
    assert created["human_verification_pending"] is True

    # 2. Hospital cannot resolve Flow A -> 403 Forbidden
    res_hosp = client.post(
        f"/api/claims/CLM-FLA-1/human-resolution",
        json={"resolution_note": "Human review decision: APPROVE", "resolved_by": "hospital"}
    )
    assert res_hosp.status_code == 403

    # 3. Insurance APPROVE -> terminal APPROVED
    res_ins_app = client.post(
        f"/api/claims/CLM-FLA-1/human-resolution",
        json={"resolution_note": "Human review decision: APPROVE. Note: override", "resolved_by": "insurance"}
    )
    assert res_ins_app.status_code == 200
    assert res_ins_app.json()["workflow_state"] == "APPROVED"

    # 4. Insurance REJECT -> terminal REJECTED
    claim2 = _scenario_claim("CLM-FLA-2", "POL-REG-LDL", metrics_extra={"ldl_value": 130})
    client2, _ = _make_test_client(chunks, pool=[])
    client2.post("/api/claims", json={"canonical_claim": claim2})

    res_ins_rej = client2.post(
        f"/api/claims/CLM-FLA-2/human-resolution",
        json={"resolution_note": "Human review decision: REJECT. Note: Rejection reason text", "resolved_by": "insurance"}
    )
    assert res_ins_rej.status_code == 200
    assert res_ins_rej.json()["workflow_state"] == "REJECTED"
    assert "Rejection reason text" in res_ins_rej.json()["decision"]["reasoning"][-1]


def test_flow_a_more_information(workflow_registry):
    chunks = [_chunk("POL-REG-LDL", "C-LDL", "LDL < 70 required")]
    claim = _scenario_claim("CLM-FLA-3", "POL-REG-LDL", metrics_extra={"ldl_value": 130})
    pool = [_ev("ldl_report", "EV-LDL-1", {"ldl_value": 55})]

    client, _ = _make_test_client(chunks, pool)
    client.post("/api/claims", json={"canonical_claim": claim})

    # Insurance MORE INFORMATION -> routes to recovery flow -> pauses at AWAITING_PROVIDER_DECISION (Flow B)
    res_ins_more = client.post(
        f"/api/claims/CLM-FLA-3/human-resolution",
        json={"resolution_note": "Human review decision: MORE_INFO. Note: request evidence", "resolved_by": "insurance"}
    )
    assert res_ins_more.status_code == 200
    res_claim = res_ins_more.json()
    assert res_claim["workflow_state"] == "HUMAN_REVIEW"
    assert res_claim["human_verification_pending"] is False  # Now Flow B!


# ---------------------------------------------------------------------------
# Flow B scenarios
# ---------------------------------------------------------------------------

def test_flow_b_provider_gate_resolutions(workflow_registry):
    chunks = [_chunk("POL-REG-LDL", "C-LDL", "LDL < 70 required")]
    claim = _scenario_claim("CLM-FLB-1", "POL-REG-LDL") # Undocumented -> RMI

    # Start with seeded pool and decline decision so it pauses in AWAITING_PROVIDER_DECISION
    client, _ = _make_test_client(chunks, pool=[_ev("ldl_report", "EV-LDL-2", {"ldl_value": 55})])
    client.post("/api/claims", json={"canonical_claim": claim, "provider_decision": "DECLINE"})

    # 1. Insurance cannot resolve Flow B -> 403 Forbidden
    res_ins = client.post(
        f"/api/claims/CLM-FLB-1/human-resolution",
        json={"resolution_note": "Human review decision: PROVIDE_INFO", "resolved_by": "insurance"}
    )
    assert res_ins.status_code == 403

    # 2. Hospital SEND INFORMATION -> V2 Agent 1 runs and approves
    res_hosp_send = client.post(
        f"/api/claims/CLM-FLB-1/human-resolution",
        json={
            "resolution_note": "Human review decision: PROVIDE_INFO. Note: send document",
            "attached_evidence": [_ev("ldl_report", "EV-LDL-2", {"ldl_value": 55})],
            "resolved_by": "hospital"
        }
    )
    assert res_hosp_send.status_code == 200
    assert res_hosp_send.json()["workflow_state"] == "APPROVED"
    assert res_hosp_send.json()["claim_version"] == 2

    # 3. Hospital DENY INFORMATION -> immediate REJECT with reason
    claim2 = _scenario_claim("CLM-FLB-2", "POL-REG-LDL")
    client2, _ = _make_test_client(chunks, pool=[_ev("ldl_report", "EV-LDL-2", {"ldl_value": 55})])
    client2.post("/api/claims", json={"canonical_claim": claim2, "provider_decision": "DECLINE"})

    res_hosp_deny = client2.post(
        f"/api/claims/CLM-FLB-2/human-resolution",
        json={
            "resolution_note": "Human review decision: REJECT. Note: Rejection reason text",
            "resolved_by": "hospital"
        }
    )
    assert res_hosp_deny.status_code == 200
    assert res_hosp_deny.json()["workflow_state"] == "REJECTED"
    assert "Rejection reason text" in res_hosp_deny.json()["decision"]["reasoning"][-1]


def test_v2_reject_and_v2_rmi(workflow_registry):
    chunks = [_chunk("POL-REG-LDL", "C-LDL", "LDL < 70 required")]
    claim = _scenario_claim("CLM-FLB-3", "POL-REG-LDL")

    client, _ = _make_test_client(chunks, pool=[_ev("ldl_report", "EV-LDL-3", {"ldl_value": 130})])
    client.post("/api/claims", json={"canonical_claim": claim, "provider_decision": "DECLINE"})

    # SEND INFO with failing evidence (130) -> V2 REJECT -> routes to Insurance Human Review (Flow A)
    res_rej = client.post(
        f"/api/claims/CLM-FLB-3/human-resolution",
        json={
            "resolution_note": "Human review decision: PROVIDE_INFO",
            "attached_evidence": [_ev("ldl_report", "EV-LDL-3", {"ldl_value": 130})],
            "resolved_by": "hospital"
        }
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["workflow_state"] == "HUMAN_REVIEW"
    assert res_rej.json()["human_verification_pending"] is True  # Routes to Flow A!

    # Setup RMI again scenario
    monkeypatch = pytest.MonkeyPatch()
    entries = {
        ("POL-REG-CAP", "C-A"): {
            "required_evidence_keys": ["extra_doc_a"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-REG-CAP", "C-B"): {
            "required_evidence_keys": ["extra_doc_b"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
    }
    for key, value in entries.items():
        monkeypatch.setitem(CRITERIA_RULES_REGISTRY, key, value)

    chunks = [
        _chunk("POL-REG-CAP", "C-A", "Req A"),
        _chunk("POL-REG-CAP", "C-B", "Req B"),
    ]
    claim_rmi = _scenario_claim("CLM-FLB-4", "POL-REG-CAP")
    client2, _ = _make_test_client(chunks, pool=[_ev("extra_doc_a", "EV-A", {"verified_facts": True})])
    client2.post("/api/claims", json={"canonical_claim": claim_rmi, "provider_decision": "DECLINE"})

    # V2 yields RMI again -> no loop -> escalates to Insurance Human Review (Flow A)
    res_rmi = client2.post(
        f"/api/claims/CLM-FLB-4/human-resolution",
        json={
            "resolution_note": "Human review decision: PROVIDE_INFO",
            "attached_evidence": [_ev("extra_doc_a", "EV-A", {"verified_facts": True})],
            "resolved_by": "hospital"
        }
    )
    assert res_rmi.status_code == 200
    res_claim = res_rmi.json()
    assert res_claim["workflow_state"] == "HUMAN_REVIEW"
    assert res_claim["human_verification_pending"] is True  # Escapes loop to Flow A!
    assert "MAX_RESUBMISSION_ATTEMPTS reached" in "".join(res_claim["human_review_reasons"])
