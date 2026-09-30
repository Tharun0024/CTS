"""Phase 2 — informational-only Agent 1 decision confidence metrics.

Contract/regression coverage:
  - confidence_score / confidence_level / confidence_factors are derived ONLY
    from existing deterministic, evidence-grounded engine signals (criterion
    states, provenance confidence, evidence quality statuses, reason codes),
  - confidence NEVER changes the frozen APPROVE/REJECT/RMI/HUMAN_REVIEW
    outcomes, reason codes, or Agent2 routing semantics,
  - the metrics persist with the claim record and every version snapshot so
    Hospital and Insurance receive identical values,
  - the fields are additive: legacy DecisionResponse constructions keep
    working unchanged (defaults None/None/[]).
"""
import pytest

from decision.decision_logic import attach_confidence_metrics, make_decision
from decision.schemas import (
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResponse,
    EvidenceItem,
    EvidenceStatus,
)
from api.claims.mapping import serialize_decision

from tests.test_decision_contract import (
    _case,
    _verified_evidence,
    contract_policy,  # noqa: F401  (pytest fixture import)
)
from tests.test_api_claims_contract import (
    _ldl_chunks,
    _ldl_pool,
    _make_client,
    api_registry,  # noqa: F401  (pytest fixture import)
)
from tests.test_agent2_v1_end_to_end import _scenario_claim


# ---------------------------------------------------------------------------
# Derivation: deterministic, grounded, per-outcome expectations
# ---------------------------------------------------------------------------

class TestConfidenceDerivation:
    def test_approve_with_verified_evidence_is_high_confidence(self, contract_policy):
        resp = make_decision(contract_policy, _case(), [_verified_evidence()])
        assert resp.outcome == DecisionOutcome.APPROVE
        assert resp.confidence_score is not None
        assert 0.8 <= resp.confidence_score <= 1.0
        assert resp.confidence_level == "HIGH"
        assert resp.confidence_factors
        assert any("PASS" in f for f in resp.confidence_factors)
        assert any("evidence confidence" in f for f in resp.confidence_factors)

    def test_missing_documentation_rmi_carries_confidence(self, contract_policy):
        from decision.schemas import CaseData

        case = CaseData(
            case_id="CASE-CONF-CONF",
            patient_age=45,
            diagnoses=["E11.9"],
            clinical_metrics={"claim_payer": "Aetna"},
        )
        resp = make_decision(contract_policy, case, evidence_list=[])
        assert resp.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
        assert resp.confidence_score is not None
        assert resp.confidence_level in {"LOW", "MEDIUM", "HIGH"}
        assert any("MISSING" in f for f in resp.confidence_factors)

    def test_conflicting_evidence_yields_low_confidence(self, contract_policy):
        contradictory = EvidenceItem(
            evidence_key="lab_report",
            evidence_id="EV-LAB-002",
            source="External Lab",
            status=EvidenceStatus.CONTRADICTORY,
            confidence_score=0.9,
            extracted_facts={"marker": 3.0},
        )
        resp = make_decision(contract_policy, _case(), [_verified_evidence(), contradictory])
        assert resp.outcome == DecisionOutcome.HUMAN_REVIEW
        assert resp.reason_code == DecisionReasonCode.EVIDENCE_CONFLICT
        assert resp.confidence_score is not None
        assert resp.confidence_level == "MEDIUM"  # 0.6*CONFLICTING(0.3) + 0.4*evidence - quality-alert penalty
        assert resp.confidence_score < 0.8
        assert any("CONFLICTING" in f for f in resp.confidence_factors)
        assert any("quality alerts" in f for f in resp.confidence_factors)

    def test_hard_reject_keeps_high_confidence_on_verified_evidence(self, contract_policy):
        resp = make_decision(contract_policy, _case(marker=7.0), [_verified_evidence(marker=7.0)])
        assert resp.outcome == DecisionOutcome.REJECT
        assert resp.reason_code == DecisionReasonCode.CRITERION_FAILED_HARD
        assert resp.confidence_score is not None
        assert resp.confidence_level in {"MEDIUM", "HIGH"}

    def test_fail_closed_path_reports_low_informational_confidence(self, contract_policy):
        resp = make_decision(contract_policy, _case(payer="UnknownPayer"), [_verified_evidence()])
        assert resp.outcome == DecisionOutcome.HUMAN_REVIEW
        assert resp.reason_code == DecisionReasonCode.UNKNOWN_PAYER
        assert resp.confidence_score == pytest.approx(0.1)
        assert resp.confidence_level == "LOW"
        assert any("Fail-closed" in f for f in resp.confidence_factors)

    def test_agent_llm_fail_closed_path_also_carries_confidence(self):
        """The DecisionAgent LLM_ASSESSMENT_FAIL_CLOSED short-circuit must use
        the SAME attach_confidence_metrics mechanism as make_decision(): the
        outcome/reason_code stay fail-closed and only informational confidence
        fields are added."""
        from decision import DecisionAgent
        from decision.llm_provider import MockLLMProvider
        from transformation.canonical_claim import build_canonical_claim
        from adapters.rag_adapter import build_rag_policy

        provider = MockLLMProvider(response_generator=lambda _p, _s: "not valid json")
        agent = DecisionAgent(llm_provider=provider)
        resp = agent.evaluate_canonical_claim(
            build_canonical_claim({
                "claim_id": "CLM-CONF-FC",
                "patient": {"patient_id": "PAT-CONF-FC", "age": 66, "gender": "Male"},
                "clinical_information": {"hba1c_report": {
                    "status": "verified", "confidence_score": 0.95,
                    "extracted_facts": {"hba1c": 8.5}}},
                "submission": {"attempt": 1, "date": "2026-08-18"},
            }),
            build_rag_policy({
                "claim_id": "CLM-CONF-FC",
                "matched_policies": [{"policy_id": "POL-CONF-FC", "name": "Confidence FC Policy"}],
                "criteria": [{"criterion_id": "CRT-HBA1C", "requirement": "HbA1c above 8.0%",
                              "mandatory": True, "required_evidence_keys": ["hba1c_report"],
                              "clinical_rule": {"field": "clinical_metrics.hba1c", "operator": "gt", "value": 8.0},
                              "evidence_rule": {"field": "hba1c", "operator": "gt", "value": 8.0}}],
            }),
        )
        # Fail-closed semantics unchanged...
        assert resp.outcome == DecisionOutcome.HUMAN_REVIEW
        assert resp.reason_code == DecisionReasonCode.LLM_ASSESSMENT_FAIL_CLOSED
        assert resp.errors
        # ...with the same informational confidence mechanism attached.
        assert resp.confidence_score == pytest.approx(0.1)
        assert resp.confidence_level == "LOW"
        assert any("Fail-closed" in f for f in resp.confidence_factors)

    def test_derivation_is_deterministic(self, contract_policy):
        first = make_decision(contract_policy, _case(), [_verified_evidence()])
        second = make_decision(contract_policy, _case(), [_verified_evidence()])
        assert first.confidence_score == second.confidence_score
        assert first.confidence_level == second.confidence_level
        assert first.confidence_factors == second.confidence_factors


# ---------------------------------------------------------------------------
# Informational only: outcomes, reason codes and routing stay frozen
# ---------------------------------------------------------------------------

class TestConfidenceNeverChangesTheDecision:
    @pytest.mark.parametrize(
        "case, evidence, expected_outcome, expected_reason",
        [
            (None, "verified", DecisionOutcome.APPROVE, DecisionReasonCode.ALL_CRITERIA_SATISFIED),
            (7.0, "verified", DecisionOutcome.REJECT, DecisionReasonCode.CRITERION_FAILED_HARD),
            ("excluded", "verified", DecisionOutcome.REJECT, DecisionReasonCode.COVERAGE_EXCLUSION),
            ("none", "none", DecisionOutcome.REQUEST_MORE_INFORMATION, DecisionReasonCode.MISSING_DOCUMENTATION),
            ("conflict", "conflict", DecisionOutcome.HUMAN_REVIEW, DecisionReasonCode.EVIDENCE_CONFLICT),
            ("unknown_payer", "verified", DecisionOutcome.HUMAN_REVIEW, DecisionReasonCode.UNKNOWN_PAYER),
        ],
        ids=["approve", "hard-reject", "exclusion-reject", "rmi", "conflict", "unknown-payer"],
    )
    def test_frozen_outcomes_survive_confidence_attachment(
        self, contract_policy, case, evidence, expected_outcome, expected_reason
    ):
        from decision.schemas import CaseData

        if case is None:
            case_data = _case()
        elif case == "excluded":
            case_data = _case(diagnoses=["E10"])
        elif case == "none":
            case_data = CaseData(
                case_id="CASE-CONF", patient_age=45, diagnoses=["E11.9"],
                clinical_metrics={"claim_payer": "Aetna"},
            )
        elif case == "conflict":
            case_data = _case()
        elif case == "unknown_payer":
            case_data = _case(payer="UnknownPayer")
        else:
            case_data = _case(marker=case)

        evidence_list = []
        if evidence == "verified":
            evidence_list = [_verified_evidence(marker=7.0 if case == 7.0 else 8.5)]
        elif evidence == "conflict":
            evidence_list = [
                _verified_evidence(),
                EvidenceItem(
                    evidence_key="lab_report", evidence_id="EV-LAB-002", source="External Lab",
                    status=EvidenceStatus.CONTRADICTORY, confidence_score=0.9,
                    extracted_facts={"marker": 3.0},
                ),
            ]

        resp = make_decision(contract_policy, case_data, evidence_list)
        assert resp.outcome == expected_outcome
        assert resp.reason_code == expected_reason
        # Routing semantics untouched by confidence attachment.
        assert resp.agent2_recoverable is (expected_outcome == DecisionOutcome.REQUEST_MORE_INFORMATION)

    def test_attach_is_pure_post_processing(self):
        resp = DecisionResponse(
            case_id="CASE-X",
            outcome=DecisionOutcome.APPROVE,
            reason_code=DecisionReasonCode.ALL_CRITERIA_SATISFIED,
        )
        attached = attach_confidence_metrics(resp)
        assert attached is resp
        assert resp.outcome == DecisionOutcome.APPROVE
        assert resp.reason_code == DecisionReasonCode.ALL_CRITERIA_SATISFIED
        assert resp.confidence_score is not None  # no evaluations -> LOW fallback


# ---------------------------------------------------------------------------
# Additive schema contract
# ---------------------------------------------------------------------------

class TestSchemaContract:
    def test_confidence_fields_default_additively(self):
        resp = DecisionResponse(case_id="CASE-X", outcome=DecisionOutcome.APPROVE)
        assert resp.confidence_score is None
        assert resp.confidence_level is None
        assert resp.confidence_factors == []

    def test_serialize_decision_carries_confidence(self, contract_policy):
        resp = make_decision(contract_policy, _case(), [_verified_evidence()])
        serialized = serialize_decision(resp)
        assert serialized["confidence_score"] == resp.confidence_score
        assert serialized["confidence_level"] == resp.confidence_level
        assert serialized["confidence_factors"] == resp.confidence_factors
        # Frozen contract fields remain present and unchanged.
        assert serialized["outcome"] == "APPROVE"
        assert serialized["status"] == "ACCEPT"
        assert serialized["reason_code"] == "ALL_CRITERIA_SATISFIED"

    def test_serialize_decision_handles_legacy_responses(self):
        legacy = DecisionResponse(case_id="CASE-X", outcome=DecisionOutcome.REJECT)
        serialized = serialize_decision(legacy)
        assert serialized["confidence_score"] is None
        assert serialized["confidence_level"] is None
        assert serialized["confidence_factors"] == []


# ---------------------------------------------------------------------------
# Persistence: Hospital and Insurance read identical confidence values
# ---------------------------------------------------------------------------

class TestApiPersistenceContract:
    def test_claim_record_and_versions_carry_identical_confidence(self, api_registry):
        client, _ = _make_client(_ldl_chunks(), _ldl_pool())
        claim = _scenario_claim("CLM-CONF-1", "POL-API-LDL")

        created = client.post("/api/claims", json={"canonical_claim": claim})
        assert created.status_code == 201
        body = created.json()

        decision = body["decision"]
        assert decision["confidence_score"] is not None
        assert decision["confidence_level"] in {"LOW", "MEDIUM", "HIGH"}
        assert isinstance(decision["confidence_factors"], list)
        assert decision["confidence_factors"]

        # GET round-trip: identical persisted values (Hospital & Insurance portals
        # both read this same record).
        detail = client.get("/api/claims/CLM-CONF-1").json()
        assert detail["decision"]["confidence_score"] == decision["confidence_score"]
        assert detail["decision"]["confidence_level"] == decision["confidence_level"]
        assert detail["decision"]["confidence_factors"] == decision["confidence_factors"]

        # Confidence persists with every version snapshot.
        versions = client.get("/api/claims/CLM-CONF-1/versions").json()
        assert versions["versions"]
        for version in versions["versions"]:
            assert "confidence_score" in version["decision"]
            assert "confidence_level" in version["decision"]
            assert "confidence_factors" in version["decision"]
