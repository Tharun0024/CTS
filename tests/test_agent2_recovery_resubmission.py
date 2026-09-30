"""Phase 3 focused tests: Agent2 recovery + resubmission on the Phase-2 contract.

Verifies the connected flow:
    Agent1 REQUEST_MORE_INFORMATION -> EvidenceRequest -> provider retrieval
    -> FOUND/MISSING -> sensitivity/release gate -> provider accept/decline
    -> V2 submission -> Agent1 re-evaluation -> final decision.

Covers: flagship recovery, missing evidence, provider decline, sensitive
evidence, hard REJECT, HUMAN_REVIEW, retry/version cap, and V1 immutability.
All tests run offline (RAG + both LLM layers mocked); Agent1 semantics are
exercised unchanged via services.run_agent2_v1_pipeline.
"""
import copy
import json

import pytest

from adapters.rag_adapter import CRITERIA_RULES_REGISTRY
from services.integrated_pipeline import (
    classify_decision_for_agent2,
    run_agent2_v1_pipeline,
)
from decision.schemas import (
    CriterionEvaluation,
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResponse,
)
from agent2.schemas.evidence_request import RequestedItemState

from tests.test_agent2_v1_end_to_end import (
    _build_components,
    _chunk,
    _ev,
    _pool_source,
    _scenario_claim,
    _all_claim_evidence_ids,
)


@pytest.fixture
def p3_registry(monkeypatch):
    """Scenario-specific structured rules for the Phase-3 policies."""
    entries = {
        ("POL-P3-FLAG", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": {"field": "clinical_metrics.ldl_value", "operator": "lt", "value": 70},
            "evidence_rule": None,
        },
        ("POL-P3-MISS", "C-MET"): {
            "required_evidence_keys": ["metformin_trial"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-P3-SENS", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-P3-HARD", "C01"): {
            "required_evidence_keys": ["diagnosis"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-P3-HR", "C01"): {
            "required_evidence_keys": ["diagnosis"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-P3-CAP", "C-A"): {
            "required_evidence_keys": ["extra_doc_a"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-P3-CAP", "C-B"): {
            "required_evidence_keys": ["extra_doc_b"],
            "clinical_rule": None,
            "evidence_rule": None,
        },
        ("POL-P3-ST", "C-ST"): {
            "required_evidence_keys": ["statin_trial"],
            "clinical_rule": {"field": "clinical_metrics.statin_duration_days", "operator": "gte", "value": 120},
            "evidence_rule": None,
        },
    }
    for key, value in entries.items():
        monkeypatch.setitem(CRITERIA_RULES_REGISTRY, key, value)


# ---------------------------------------------------------------------------
# Flagship recovery: MORE_INFO -> EvidenceRequest -> FOUND -> V2 -> APPROVE
# ---------------------------------------------------------------------------

class TestFlagshipRecoveryFlow:
    def test_more_info_recovered_to_v2_and_approved(self, p3_registry):
        chunks = [_chunk("POL-P3-FLAG", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P3-FLAG", "POL-P3-FLAG")

        pool = [_ev("ldl_report", "EV-P3-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        # Full flow completed: V1 RMI -> Agent2 -> V2 -> Agent1 APPROVE.
        assert result.final_outcome == DecisionOutcome.APPROVE
        assert result.agent2_invoked is True
        assert result.resubmissions == 1
        assert len(result.versions) == 2
        assert result.versions[0]["decision"].outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
        assert result.versions[1]["new_evidence_delta"] == ["EV-P3-LDL"]

        # Agent2 received the structured EvidenceRequest (request-only payload).
        request = result.evidence_request
        assert request is not None
        assert request.claim_id == "CLM-P3-FLAG"
        assert request.claim_version == 1
        assert request.evidence_request_id.startswith("ERQ-")
        assert request.correlation_id == "CORR-CLM-P3-FLAG-V1"
        assert "ldl_report" in request.evidence_keys
        assert not request.model_fields_set.intersection(
            {"member_id", "plan_id", "payer_context"}
        ), "EvidenceRequest must never carry payer-side data"

        # FOUND/MISSING tracking on the recovery result (FOUND != SATISFIED).
        recovery = result.recovery_result
        assert recovery is not None
        assert recovery.evidence_request_id == request.evidence_request_id
        assert recovery.all_requested_found is True
        item = recovery.item_results[0]
        assert item.state == RequestedItemState.FOUND
        assert item.evidence_ids == ["EV-P3-LDL"]
        # Real provenance preserved across the boundary.
        assert any(ev.evidence_id == "EV-P3-LDL" for ev in recovery.recovered_evidence)

        # Submission released with the real delta.
        assert result.submissions[0]["new_evidence_delta"] == ["EV-P3-LDL"]
        assert result.submissions[0]["released"] is True

    def test_found_does_not_imply_satisfied(self, p3_registry):
        """FOUND evidence that cannot demonstrate the required fact must not
        produce APPROVE: satisfaction is Agent1's re-evaluation only."""
        chunks = [_chunk("POL-P3-FLAG", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P3-FLAG2", "POL-P3-FLAG")

        # Record exists (FOUND) but the LDL value does not meet the threshold.
        pool = [_ev("ldl_report", "EV-P3-LDL-HI", {"ldl_value": 130, "content_reference": "LDL 130 mg/dL"})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.recovery_result is not None
        assert result.recovery_result.all_requested_found is True  # FOUND...
        assert result.final_outcome != DecisionOutcome.APPROVE      # ...but NOT satisfied
        assert result.resubmissions == 1


# ---------------------------------------------------------------------------
# Missing evidence stays MISSING: no V2, no fabrication
# ---------------------------------------------------------------------------

class TestMissingEvidence:
    def test_missing_evidence_escalates_without_v2(self, p3_registry):
        chunks = [_chunk("POL-P3-MISS", "C-MET", "Documented metformin trial required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P3-MISS", "POL-P3-MISS")

        # Pool has records, but none is metformin evidence.
        pool = [_ev("ldl_report", "EV-P3-LDL", {"ldl_value": 55})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert result.resubmissions == 0
        assert len(result.versions) == 1

        # Contract tracked the item as MISSING with no evidence references.
        recovery = result.recovery_result
        assert recovery is not None
        item = recovery.item_results[0]
        assert item.state == RequestedItemState.MISSING
        assert item.evidence_ids == []
        assert item.provenance == []
        # Anti-fabrication: nothing entered any version beyond V1 evidence.
        assert set(_all_claim_evidence_ids(result)) <= {"EV-DX-1"}


# ---------------------------------------------------------------------------
# Provider decline stops the resubmission
# ---------------------------------------------------------------------------

class TestProviderDecline:
    def test_provider_decline_blocks_v2(self, p3_registry):
        chunks = [_chunk("POL-P3-FLAG", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P3-DECL", "POL-P3-FLAG")

        pool = [_ev("ldl_report", "EV-P3-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]
        result = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source(pool), provider_decision="DECLINE"
        )

        assert result.provider_declined is True
        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert result.human_review_required is True
        assert result.resubmissions == 0
        assert len(result.versions) == 1          # no V2 without provider consent
        assert result.submissions == []
        # Recovered-but-declined record never enters any claim version.
        assert "EV-P3-LDL" not in _all_claim_evidence_ids(result)
        # Recovery still happened and was tracked (decline is a consent gate).
        assert result.recovery_result is not None
        assert result.recovery_result.all_requested_found is True


# ---------------------------------------------------------------------------
# Sensitive evidence cannot enter V2
# ---------------------------------------------------------------------------

class TestSensitiveEvidence:
    def test_protected_evidence_blocked_by_release_gate(self, p3_registry):
        chunks = [_chunk("POL-P3-SENS", "C-LDL", "Documented LDL report required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P3-SENS", "POL-P3-SENS")

        pool = [_ev("ldl_report", "EV-P3-SENS", {"ldl_value": 60}, sensitivity="PROTECTED_HIV")]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert result.sensitive_blocked is True
        assert result.resubmissions == 0
        assert len(result.versions) == 1
        assert "EV-P3-SENS" not in _all_claim_evidence_ids(result)

    def test_unknown_sensitivity_is_blocked_too(self, p3_registry):
        chunks = [_chunk("POL-P3-SENS", "C-LDL", "Documented LDL report required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P3-UNK", "POL-P3-SENS")

        pool = [_ev("ldl_report", "EV-P3-UNK", {"ldl_value": 60}, sensitivity="")]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.sensitive_blocked is True
        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert "EV-P3-UNK" not in _all_claim_evidence_ids(result)


# ---------------------------------------------------------------------------
# Routing gates: hard REJECT and HUMAN_REVIEW never enter recovery
# ---------------------------------------------------------------------------

class TestRoutingGates:
    def test_hard_reject_never_enters_recovery(self, p3_registry):
        chunks = [_chunk("POL-P3-HARD", "C01", "Diagnosis documentation required.")]
        exclusions = [{
            "exclusion_id": "EX-AGE",
            "name": "Age exclusion",
            "rule": {"field": "patient_age", "operator": "gte", "value": 80},
            "required_evidence_keys": [],
        }]
        components = _build_components(chunks, exclusions=exclusions)
        claim = _scenario_claim("CLM-P3-HARD", "POL-P3-HARD", age=85)

        pool = [_ev("ldl_report", "EV-P3-LDL", {"ldl_value": 55})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.REJECT
        assert result.agent2_invoked is False
        assert result.evidence_request is None
        assert result.recovery_result is None
        assert result.resubmissions == 0
        assert len(result.versions) == 1

    def test_human_review_never_enters_recovery(self, p3_registry):
        chunks = [_chunk("POL-P3-HR", "C01", "Diagnosis documentation required.")]
        components = _build_components(chunks)
        claim = _scenario_claim(
            "CLM-P3-HR", "POL-P3-HR",
            evidence=[
                _ev("diagnosis", "EV-DX-A", {"verified_facts": True, "note": "OA right knee"}),
                _ev("diagnosis", "EV-DX-B", {"verified_facts": False, "note": "contradicting"}),
            ],
        )

        pool = [_ev("diagnosis", "EV-DX-C", {"verified_facts": True})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert result.agent2_invoked is False
        assert result.evidence_request is None
        assert result.recovery_result is None
        assert result.resubmissions == 0
        assert len(result.versions) == 1


# ---------------------------------------------------------------------------
# Frozen routing classifier: RMI is the ONLY Agent2-recoverable outcome
# ---------------------------------------------------------------------------

def _bare_decision(outcome, exclusion_results=None):
    return DecisionResponse(
        case_id="CASE-ROUTE",
        outcome=outcome,
        exclusion_results=exclusion_results or {},
    )


class TestFrozenRoutingClassifier:
    """classify_decision_for_agent2 must implement the frozen V1 routing:
    REQUEST_MORE_INFORMATION is the ONLY recoverable outcome; every REJECT
    (hard criterion failure OR coverage exclusion) is terminal."""

    def test_rmi_is_the_only_recoverable_outcome(self):
        decision = _bare_decision(
            DecisionOutcome.REQUEST_MORE_INFORMATION,
        )
        assert classify_decision_for_agent2(decision) == "RECOVERABLE"

    @pytest.mark.parametrize("outcome", [
        DecisionOutcome.APPROVE,
        DecisionOutcome.HUMAN_REVIEW,
    ])
    def test_approve_and_human_review_are_terminal(self, outcome):
        assert classify_decision_for_agent2(_bare_decision(outcome)) == "TERMINAL"

    def test_reject_with_exclusion_is_terminal(self):
        decision = _bare_decision(
            DecisionOutcome.REJECT,
            exclusion_results={"EXC-AGE": True},
        )
        assert classify_decision_for_agent2(decision) == "TERMINAL"

    def test_reject_without_exclusion_is_still_terminal(self):
        """Hard criterion failure REJECT (no exclusion triggered) must NOT
        become Agent2-recoverable: there is no generic REJECT -> Agent2 path."""
        decision = _bare_decision(DecisionOutcome.REJECT)
        assert not any(decision.exclusion_results.values())
        assert classify_decision_for_agent2(decision) == "TERMINAL"


# ---------------------------------------------------------------------------
# Documented hard criterion failure -> terminal REJECT, Agent2 never invoked
# ---------------------------------------------------------------------------

class TestHardCriterionFailureIsTerminal:
    def test_documented_hard_failure_rejects_without_agent2(self, p3_registry):
        """LDL value IS documented (130) but definitively fails the rule:
        that is a hard REJECT, never an RMI, and Agent2 must not run even
        though the provider pool contains evidence that would 'fix' it."""
        chunks = [_chunk("POL-P3-FLAG", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim(
            "CLM-P3-HF", "POL-P3-FLAG",
            metrics_extra={"ldl_value": 130},  # present in data but failing
        )

        pool = [_ev("ldl_report", "EV-P3-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        v1 = result.versions[0]["decision"]
        assert v1.outcome == DecisionOutcome.REJECT
        assert v1.agent2_recoverable is False
        assert classify_decision_for_agent2(v1) == "TERMINAL"

        assert result.final_outcome == DecisionOutcome.REJECT
        assert result.agent2_invoked is False
        assert result.evidence_request is None
        assert result.recovery_result is None
        assert result.resubmissions == 0
        assert len(result.versions) == 1
        # The pool evidence that could have 'fixed' the failure never enters
        # any claim version (Agent2 never ran).
        assert "EV-P3-LDL" not in _all_claim_evidence_ids(result)


# ---------------------------------------------------------------------------
# Documentation insufficiency is REQUEST_MORE_INFORMATION -> Agent2 recovery
# ---------------------------------------------------------------------------

class TestDocumentationInsufficiencyIsRMI:
    def test_undocumented_fact_is_rmi_not_reject_and_recovers(self, p3_registry):
        """The statin trial duration is simply undocumented in V1 (metric
        absent): that must surface as REQUEST_MORE_INFORMATION (never as a
        recoverable REJECT) and complete the Agent2 recovery flow."""
        chunks = [_chunk("POL-P3-ST", "C-ST", "At least 120 days of statin step therapy documented.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P3-ST", "POL-P3-ST")  # no statin metric documented

        pool = [
            _ev("statin_trial", "EV-P3-ST-150",
                {"statin_duration_days": 150, "content_reference": "Atorvastatin 150-day trial"}),
        ]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        v1 = result.versions[0]["decision"]
        assert v1.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
        assert v1.agent2_recoverable is True
        assert classify_decision_for_agent2(v1) == "RECOVERABLE"

        assert result.agent2_invoked is True
        assert result.evidence_request is not None
        assert "statin_trial" in result.evidence_request.evidence_keys
        assert result.final_outcome == DecisionOutcome.APPROVE
        assert result.resubmissions == 1
        assert result.versions[1]["new_evidence_delta"] == ["EV-P3-ST-150"]


# ---------------------------------------------------------------------------
# Retry/version cap and V1 immutability
# ---------------------------------------------------------------------------

class TestLimitsAndImmutability:
    def test_retry_cap_stops_loop_and_history_is_intact(self, p3_registry):
        chunks = [
            _chunk("POL-P3-CAP", "C-A", "Extra documentation A required."),
            _chunk("POL-P3-CAP", "C-B", "Extra documentation B required."),
        ]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P3-CAP", "POL-P3-CAP")

        # Only doc A is ever recoverable; doc B stays MISSING forever.
        pool = [_ev("extra_doc_a", "EV-P3-DOC-A", {"verified_facts": True})]
        result = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source(pool), max_resubmissions=1
        )

        assert result.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert result.resubmissions == 1
        assert len(result.versions) == 2
        assert result.versions[0]["version"] == "V1"
        assert result.versions[1]["version"] == "V2"
        assert "MAX_RESUBMISSION_ATTEMPTS" in " ".join(result.human_review_reasons)
        # The final recovery result tracked doc B as MISSING (no fabrication).
        assert result.recovery_result is not None
        assert result.recovery_result.missing_requests, "doc B must remain MISSING"

    def test_v1_claim_snapshot_is_immutable(self, p3_registry):
        chunks = [_chunk("POL-P3-FLAG", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-P3-IMM", "POL-P3-FLAG")
        original = copy.deepcopy(claim)

        pool = [_ev("ldl_report", "EV-P3-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]
        result = run_agent2_v1_pipeline(claim, components, recovery_source=_pool_source(pool))

        assert result.final_outcome == DecisionOutcome.APPROVE
        # Caller's canonical claim is never mutated by the pipeline.
        assert claim == original
        # The stored V1 snapshot still carries exactly the original evidence
        # and never the recovered record; only V2 does.
        v1_ids = [e["evidence_id"] for e in result.versions[0]["claim"]["evidence"]]
        assert v1_ids == ["EV-DX-1"]
        assert result.versions[0]["claim"]["case_data"]["clinical_metrics"].get("ldl_value") is None
        v2_ids = [e["evidence_id"] for e in result.versions[1]["claim"]["evidence"]]
        assert v2_ids == ["EV-DX-1", "EV-P3-LDL"]
