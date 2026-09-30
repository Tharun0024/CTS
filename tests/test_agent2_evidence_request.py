"""Phase 2 focused tests: Agent2 evidence-request contract.

Covers the frozen V1 routing gate and provider-side evidence recovery:
  A. valid REQUEST_MORE_INFORMATION -> Agent2 receives the correct structured
     EvidenceRequest (identity, correlation, requested content preserved).
  B. provider evidence FOUND with real evidence IDs and provenance.
  C. requested evidence MISSING stays MISSING (no fabrication).
  D. hard REJECT never invokes Agent2.
  E. HUMAN_REVIEW never invokes Agent2.

Plus contract guards: FOUND != SATISFIED, no coverage-decision fields in the
recovery result, and the Agent2 trust boundary (no payer DB references).
"""

import sqlite3
from pathlib import Path

import pytest

from decision.schemas import (
    CriterionEvaluation,
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResponse,
)
from agent2.recovery import EvidenceRecoveryHandler, route_agent1_decision
from agent2.schemas.evidence import EvidenceState
from agent2.schemas.evidence_request import (
    EvidenceRecoveryResult,
    EvidenceRequest,
    RequestedItemResult,
    RequestedItemState,
)
from agent2.database import db_manager

PATIENT_ID = "PAT-P2"
CLAIM_ID = "CLM-P2-001"
CLAIM_VERSION = 2

LDL_REQUEST = "LDL threshold met (CRIT-LDL): ldl_value"
MED_REQUEST = "Qualifying medication trial (CRIT-MED): metformin_trial"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def provider_db(tmp_path, monkeypatch):
    """Isolated provider-side SQLite warehouse (Agent2's ONLY data interface)."""
    db_path = str(tmp_path / "agent2_test.db")
    monkeypatch.setattr(db_manager, "DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Provider clinical tables only -- mirroring db_manager.init_db schema.
    cur.execute(
        "CREATE TABLE patients (patient_id TEXT PRIMARY KEY, name TEXT NOT NULL,"
        " dob TEXT, gender TEXT, address TEXT)"
    )
    cur.execute(
        "CREATE TABLE conditions (id TEXT PRIMARY KEY, patient_id TEXT, code TEXT,"
        " system TEXT, display TEXT, onset TEXT, status TEXT)"
    )
    cur.execute(
        "CREATE TABLE medications (id TEXT PRIMARY KEY, patient_id TEXT, code TEXT,"
        " system TEXT, display TEXT, date TEXT, status TEXT, doctor TEXT)"
    )
    cur.execute(
        "CREATE TABLE observations (id TEXT PRIMARY KEY, patient_id TEXT, code TEXT,"
        " system TEXT, display TEXT, value REAL, unit TEXT, date TEXT)"
    )
    cur.execute(
        "CREATE TABLE procedures (id TEXT PRIMARY KEY, patient_id TEXT, code TEXT,"
        " system TEXT, display TEXT, date TEXT, status TEXT, doctor TEXT)"
    )
    cur.execute(
        "CREATE TABLE encounters (id TEXT PRIMARY KEY, patient_id TEXT, code TEXT,"
        " system TEXT, display TEXT, date TEXT, status TEXT)"
    )
    cur.execute(
        "CREATE TABLE documents (id TEXT PRIMARY KEY, patient_id TEXT, title TEXT,"
        " content TEXT, type TEXT, date TEXT)"
    )

    # Seed: one real LDL observation; deliberately NO metformin record.
    cur.execute(
        "INSERT INTO patients VALUES (?, ?, ?, ?, ?)",
        (PATIENT_ID, "Phase Two Patient", "1970-01-01", "M", "1 Test Way"),
    )
    cur.execute(
        "INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "OBS-P2-01",
            PATIENT_ID,
            "18262-6",
            "http://loinc.org",
            "Low Density Lipoprotein Cholesterol [LDL-C]",
            135.0,
            "mg/dL",
            "2026-08-01T08:00:00Z",
        ),
    )
    conn.commit()
    conn.close()
    return db_path


def make_rmi_decision(requested_information=None) -> DecisionResponse:
    """A real Agent1 REQUEST_MORE_INFORMATION decision with Phase-1 fields."""
    return DecisionResponse(
        case_id="PA-P2-001",
        claim_id=CLAIM_ID,
        outcome=DecisionOutcome.REQUEST_MORE_INFORMATION,
        policy_id="CPB-TEST-P2",
        reason_code=DecisionReasonCode.MISSING_DOCUMENTATION,
        criteria_evaluations={
            "CRIT-LDL": CriterionEvaluation(criterion_id="CRIT-LDL", state="MISSING"),
            "CRIT-MED": CriterionEvaluation(criterion_id="CRIT-MED", state="MISSING"),
            "CRIT-OK": CriterionEvaluation(criterion_id="CRIT-OK", state="PASS"),
        },
        evidence_status={"ldl_value": "missing", "metformin_trial": "missing"},
        requested_information=(
            requested_information
            if requested_information is not None
            else [LDL_REQUEST, MED_REQUEST]
        ),
        agent2_recoverable=True,
    )


# ---------------------------------------------------------------------------
# A. Valid MORE_INFO request -> Agent2 receives the correct structured request
# ---------------------------------------------------------------------------

class TestARequestRouting:
    def test_rmi_produces_evidence_request_with_full_identity(self):
        request = route_agent1_decision(
            make_rmi_decision(),
            patient_id=PATIENT_ID,
            claim_version=CLAIM_VERSION,
            correlation_id="CORR-P2-XYZ",
        )
        assert isinstance(request, EvidenceRequest)
        assert request.claim_id == CLAIM_ID
        assert request.claim_version == CLAIM_VERSION
        assert request.patient_id == PATIENT_ID
        assert request.correlation_id == "CORR-P2-XYZ"
        assert request.evidence_request_id.startswith("ERQ-")

    def test_rmi_request_carries_structured_content(self):
        request = route_agent1_decision(
            make_rmi_decision(), patient_id=PATIENT_ID, claim_version=CLAIM_VERSION
        )
        assert request.requested_information == [LDL_REQUEST, MED_REQUEST]
        assert request.criterion_ids == ["CRIT-LDL", "CRIT-MED"]
        assert request.evidence_keys == ["ldl_value", "metformin_trial"]
        assert request.policy_id == "CPB-TEST-P2"
        assert request.source_reason_code == "MISSING_DOCUMENTATION"

    def test_default_correlation_id_derived_from_claim_identity(self):
        request = route_agent1_decision(
            make_rmi_decision(), patient_id=PATIENT_ID, claim_version=CLAIM_VERSION
        )
        assert request.correlation_id == f"CORR-{CLAIM_ID}-V{CLAIM_VERSION}"

    def test_approve_does_not_invoke_agent2(self):
        decision = DecisionResponse(
            case_id="PA-P2-001",
            claim_id=CLAIM_ID,
            outcome=DecisionOutcome.APPROVE,
            reason_code=DecisionReasonCode.ALL_CRITERIA_SATISFIED,
        )
        assert route_agent1_decision(
            decision, patient_id=PATIENT_ID, claim_version=CLAIM_VERSION
        ) is None

    def test_rmi_without_request_content_does_not_invoke_agent2(self):
        decision = DecisionResponse(
            case_id="PA-P2-001",
            claim_id=CLAIM_ID,
            outcome=DecisionOutcome.REQUEST_MORE_INFORMATION,
            reason_code=DecisionReasonCode.MISSING_DOCUMENTATION,
            agent2_recoverable=True,
        )
        assert route_agent1_decision(
            decision, patient_id=PATIENT_ID, claim_version=CLAIM_VERSION
        ) is None


# ---------------------------------------------------------------------------
# B. Provider evidence FOUND with real IDs and provenance
# ---------------------------------------------------------------------------

class TestBFoundEvidence:
    def test_found_item_carries_real_evidence_id_and_provenance(self, provider_db):
        request = route_agent1_decision(
            make_rmi_decision(requested_information=[LDL_REQUEST]),
            patient_id=PATIENT_ID,
            claim_version=CLAIM_VERSION,
        )
        result = EvidenceRecoveryHandler().process(request)

        assert len(result.item_results) == 1
        item = result.item_results[0]
        assert item.state == RequestedItemState.FOUND
        assert item.evidence_ids == ["EV-OBS-OBS-P2-01"]
        assert item.criterion_id == "CRIT-LDL"
        assert item.evidence_key == "ldl_value"

        prov = item.provenance[0]
        assert prov.evidence_id == "EV-OBS-OBS-P2-01"
        assert prov.source_type == "observations"
        assert prov.source_record_id == "OBS-P2-01"
        assert prov.event_date == "2026-08-01T08:00:00Z"

    def test_recovered_evidence_contains_only_real_found_records(self, provider_db):
        request = route_agent1_decision(
            make_rmi_decision(requested_information=[LDL_REQUEST]),
            patient_id=PATIENT_ID,
            claim_version=CLAIM_VERSION,
        )
        result = EvidenceRecoveryHandler().process(request)

        assert len(result.recovered_evidence) == 1
        ev = result.recovered_evidence[0]
        assert ev.evidence_id == "EV-OBS-OBS-P2-01"
        assert ev.state == EvidenceState.FOUND
        assert ev.patient_id == PATIENT_ID
        assert "135.0" in ev.content and "mg/dL" in ev.content


# ---------------------------------------------------------------------------
# C. Requested evidence MISSING stays MISSING (no fabrication)
# ---------------------------------------------------------------------------

class TestCMissingEvidence:
    def test_missing_item_stays_missing_without_evidence(self, provider_db):
        request = route_agent1_decision(
            make_rmi_decision(requested_information=[MED_REQUEST]),
            patient_id=PATIENT_ID,
            claim_version=CLAIM_VERSION,
        )
        result = EvidenceRecoveryHandler().process(request)

        assert len(result.item_results) == 1
        item = result.item_results[0]
        assert item.state == RequestedItemState.MISSING
        assert item.evidence_ids == []
        assert item.provenance == []
        assert result.recovered_evidence == []
        assert result.missing_requests == [MED_REQUEST]
        assert result.all_requested_found is False
        assert any("no evidence was fabricated" in note for note in result.notes)

    def test_mixed_found_and_missing_preserves_both_states(self, provider_db):
        request = route_agent1_decision(
            make_rmi_decision(), patient_id=PATIENT_ID, claim_version=CLAIM_VERSION
        )
        result = EvidenceRecoveryHandler().process(request)

        states = {item.request_text: item.state for item in result.item_results}
        assert states[LDL_REQUEST] == RequestedItemState.FOUND
        assert states[MED_REQUEST] == RequestedItemState.MISSING
        # Only the real FOUND record crosses the boundary.
        assert [ev.evidence_id for ev in result.recovered_evidence] == ["EV-OBS-OBS-P2-01"]

    def test_result_echoes_claim_identity_and_correlation(self, provider_db):
        request = route_agent1_decision(
            make_rmi_decision(),
            patient_id=PATIENT_ID,
            claim_version=CLAIM_VERSION,
            correlation_id="CORR-P2-XYZ",
        )
        result = EvidenceRecoveryHandler().process(request)
        assert result.evidence_request_id == request.evidence_request_id
        assert result.correlation_id == "CORR-P2-XYZ"
        assert result.claim_id == CLAIM_ID
        assert result.claim_version == CLAIM_VERSION
        assert result.patient_id == PATIENT_ID

    def test_schema_forbids_found_without_ids_and_missing_with_ids(self):
        with pytest.raises(ValueError):
            RequestedItemResult(
                request_text="x", state=RequestedItemState.FOUND, evidence_ids=[]
            )
        with pytest.raises(ValueError):
            RequestedItemResult(
                request_text="x",
                state=RequestedItemState.MISSING,
                evidence_ids=["EV-FAKE-1"],
            )


# ---------------------------------------------------------------------------
# D. Hard REJECT never invokes Agent2
# ---------------------------------------------------------------------------

class TestDHardRejectRouting:
    @pytest.mark.parametrize(
        "reason_code",
        [
            DecisionReasonCode.CRITERION_FAILED_HARD,
            DecisionReasonCode.COVERAGE_EXCLUSION,
        ],
    )
    def test_hard_reject_returns_no_evidence_request(self, reason_code):
        decision = DecisionResponse(
            case_id="PA-P2-001",
            claim_id=CLAIM_ID,
            outcome=DecisionOutcome.REJECT,
            reason_code=reason_code,
            criteria_evaluations={
                "CRIT-LDL": CriterionEvaluation(criterion_id="CRIT-LDL", state="FAIL")
            },
            # Even if callers try to smuggle recovery content, the contract
            # strips it from every non-RMI outcome (Phase-1 validator).
            requested_information=[LDL_REQUEST],
            agent2_recoverable=True,
        )
        assert decision.agent2_recoverable is False
        assert decision.requested_information == []
        assert route_agent1_decision(
            decision, patient_id=PATIENT_ID, claim_version=CLAIM_VERSION
        ) is None


# ---------------------------------------------------------------------------
# E. HUMAN_REVIEW never invokes Agent2 directly
# ---------------------------------------------------------------------------

class TestEHumanReviewRouting:
    def test_human_review_returns_no_evidence_request(self):
        decision = DecisionResponse(
            case_id="PA-P2-001",
            claim_id=CLAIM_ID,
            outcome=DecisionOutcome.HUMAN_REVIEW,
            reason_code=DecisionReasonCode.ENGINE_FAIL_CLOSED,
            requested_information=[LDL_REQUEST],
            agent2_recoverable=True,
        )
        assert decision.agent2_recoverable is False
        assert route_agent1_decision(
            decision, patient_id=PATIENT_ID, claim_version=CLAIM_VERSION
        ) is None


# ---------------------------------------------------------------------------
# Contract guards: FOUND != SATISFIED, no coverage decisions, trust boundary
# ---------------------------------------------------------------------------

class TestContractGuards:
    def test_requested_item_state_has_no_satisfied_member(self):
        assert {member.value for member in RequestedItemState} == {"FOUND", "MISSING"}

    def test_recovery_result_carries_no_coverage_decision_fields(self):
        forbidden = {
            "outcome",
            "decision",
            "approved",
            "rejected",
            "coverage_decision",
            "satisfied",
        }
        assert not forbidden.intersection(EvidenceRecoveryResult.model_fields)
        assert not forbidden.intersection(RequestedItemResult.model_fields)

    def test_agent2_sources_never_reference_payer_database(self):
        agent2_root = Path(__file__).resolve().parent.parent / "agent2"
        offenders = []
        for py_file in agent2_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            if "payer_data" in text or "payer_data.db" in text:
                offenders.append(str(py_file))
        assert offenders == [], f"Agent2 must never access the payer DB: {offenders}"
