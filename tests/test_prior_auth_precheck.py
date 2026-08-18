"""Phase 1 — deterministic Prior Authorization pre-check BEFORE Agent 1.

Verifies:
  - the explicit rule engine (requires_prior_auth, matched_rule, reason,
    policy_reference, source) backed ONLY by existing policy/benefit data,
  - determinism, explainability, fail-closed behavior and NO LLM usage,
  - explicit representation on the existing workflow control plane without
    altering the frozen state machine or the exact event trail,
  - routing: auth-required claims flow through the EXISTING authorization /
    review path (RAG -> Agent 1 -> frozen routing incl. Agent 2 recovery and
    human review); no-auth claims route directly to the existing Agent 1 V1
    evaluation with no behavior change,
  - regression: frozen V1 trails, IDs, versions and human-resolution re-entry
    are preserved, and the API claim record exposes the pre-check.

All tests run fully offline using the same mocked RAG/LLM components as
tests/test_agent2_v1_end_to_end.py.
"""
import dataclasses
import inspect

import pytest

from adapters.rag_adapter import CRITERIA_RULES_REGISTRY
from agent2.workflow.control_plane import (
    ClaimWorkflowState,
    IllegalWorkflowTransition,
    WorkflowControlPlane,
)
from decision.schemas import DecisionOutcome
from services.integrated_pipeline import (
    reenter_after_human_resolution,
    run_agent2_v1_pipeline,
)
from services.prior_auth_precheck import (
    RULE_BENEFIT_AUTHORIZATION,
    RULE_CLAIM_POLICY_REFERENCE,
    RULE_DEFAULT_NO_AUTH,
    RULE_FAIL_CLOSED,
    RULE_POLICY_CORPUS,
    PriorAuthPrecheckResult,
    PriorAuthRuleEngine,
    run_prior_auth_precheck,
)

from tests.test_agent2_v1_end_to_end import (
    _build_components,
    _chunk,
    _ev,
    _pool_source,
    _scenario_claim,
)
from tests.test_api_claims_contract import (
    _ldl_chunks,
    _ldl_pool,
    _make_client,
    api_registry,  # noqa: F401  (pytest fixture import)
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def pa_registry(monkeypatch):
    """Structured Agent-1 rules for the Phase-1 pre-check policies."""
    entries = {
        ("POL-PA-REQ", "C-LDL"): {
            "required_evidence_keys": ["ldl_report"],
            "clinical_rule": {"field": "clinical_metrics.ldl_value", "operator": "lt", "value": 70},
            "evidence_rule": None,
        },
        ("POL-PA-NONE", "C-ST"): {
            "required_evidence_keys": ["statin_trial"],
            "clinical_rule": {"field": "clinical_metrics.statin_duration_days", "operator": "gte", "value": 120},
            "evidence_rule": None,
        },
    }
    for key, value in entries.items():
        monkeypatch.setitem(CRITERIA_RULES_REGISTRY, key, value)


def _policy_record(policy_id, codes, payer="CMS (Medicare)", title="Coverage Policy"):
    return {
        "policy_id": policy_id,
        "payer": payer,
        "policy_title": title,
        "procedure_codes": list(codes),
    }


def _precheck_claim(procedures=("33207",), policy_id=None, payer_context=None,
                    procedure_description=None):
    metrics = {"claim_scenario_type": "COMPLETE"}
    if policy_id:
        metrics["claim_policy_id"] = policy_id
    if procedure_description:
        metrics["claim_procedure"] = procedure_description
    claim = {
        "claim_id": "CLM-UT",
        "patient_id": "P-1",
        "submission": {"attempt": 1, "date": "2026-08-16T00:00:00Z"},
        "case_data": {
            "case_id": "CLM-UT",
            "patient_age": 60,
            "diagnoses": [],
            "procedures": list(procedures),
            "clinical_metrics": metrics,
        },
        "evidence": [],
    }
    if payer_context is not None:
        claim["payer_context"] = payer_context
    return claim


# ---------------------------------------------------------------------------
# Rule engine: deterministic, explainable, data-backed, LLM-free
# ---------------------------------------------------------------------------

class TestPriorAuthRuleEngine:
    def test_corpus_exact_procedure_match_requires_auth(self):
        engine = PriorAuthRuleEngine(
            policy_records=[_policy_record("NCD-20.8.3", ["33206", "33207", "33208"],
                                           title="Cardiac Pacemakers")],
            source_label="unit-corpus",
        )
        result = engine.evaluate(_precheck_claim(procedures=("33207",)))
        assert result.requires_prior_auth is True
        assert result.matched_rule == RULE_POLICY_CORPUS
        assert result.policy_reference == "NCD-20.8.3"
        assert result.source == "unit-corpus"
        assert "33207" in result.reason and "NCD-20.8.3" in result.reason

    def test_corpus_numeric_range_match_requires_auth(self):
        engine = PriorAuthRuleEngine(
            policy_records=[_policy_record("NCD-20.4", ["33202-33273"])]
        )
        result = engine.evaluate(_precheck_claim(procedures=("33249",)))
        assert result.requires_prior_auth is True
        assert result.matched_rule == RULE_POLICY_CORPUS
        assert result.policy_reference == "NCD-20.4"

    def test_corpus_alphanumeric_range_match_requires_auth(self):
        engine = PriorAuthRuleEngine(
            policy_records=[_policy_record("NCD-20.4", ["C7537-C7540"])]
        )
        assert engine.evaluate(_precheck_claim(procedures=("C7538",))).requires_prior_auth is True
        assert engine.evaluate(_precheck_claim(procedures=("C7541",))).requires_prior_auth is False

    def test_no_rule_match_defaults_to_no_auth(self):
        engine = PriorAuthRuleEngine(
            policy_records=[_policy_record("NCD-20.8.3", ["33206"])]
        )
        result = engine.evaluate(_precheck_claim(procedures=("99999",)))
        assert result.requires_prior_auth is False
        assert result.matched_rule == RULE_DEFAULT_NO_AUTH
        assert result.policy_reference is None
        assert "not required" in result.reason

    def test_benefit_authorization_rule_requires_auth(self):
        payer_context = {
            "plan_id": "PLAN-AETNA-001",
            "benefits": [
                {"benefit_id": "BEN-001", "benefit_category": "Orthopedics",
                 "authorization_requirement": True},
            ],
        }
        engine = PriorAuthRuleEngine(policy_records=[])
        result = engine.evaluate(
            _precheck_claim(procedures=("27447",), payer_context=payer_context)
        )
        assert result.requires_prior_auth is True
        assert result.matched_rule == RULE_BENEFIT_AUTHORIZATION
        assert result.policy_reference == "BEN-001 (plan PLAN-AETNA-001)"
        assert "benefit" in result.source

    def test_benefit_category_resolved_from_procedure_description(self):
        payer_context = {
            "plan_id": "PLAN-AETNA-001",
            "benefits": [
                {"benefit_id": "BEN-001", "benefit_category": "Orthopedics",
                 "authorization_requirement": True},
            ],
        }
        engine = PriorAuthRuleEngine(policy_records=[])
        result = engine.evaluate(
            _precheck_claim(procedures=(), payer_context=payer_context,
                            procedure_description="Total Knee Arthroplasty (TKA)")
        )
        assert result.requires_prior_auth is True
        assert result.matched_rule == RULE_BENEFIT_AUTHORIZATION

    def test_benefit_without_authorization_requirement_is_no_auth(self):
        payer_context = {
            "plan_id": "PLAN-AETNA-001",
            "benefits": [
                {"benefit_id": "BEN-001", "benefit_category": "Orthopedics",
                 "authorization_requirement": False},
            ],
        }
        engine = PriorAuthRuleEngine(policy_records=[])
        result = engine.evaluate(
            _precheck_claim(procedures=("27447",), payer_context=payer_context)
        )
        assert result.requires_prior_auth is False
        assert result.matched_rule == RULE_DEFAULT_NO_AUTH

    def test_claim_policy_reference_rule_requires_auth(self):
        engine = PriorAuthRuleEngine(
            policy_records=[_policy_record("POL-X", ["99999"], payer="Aetna")]
        )
        # Procedure does not match, but the claim explicitly references a
        # policy that exists in the corpus.
        result = engine.evaluate(
            _precheck_claim(procedures=("11111",), policy_id="POL-X")
        )
        assert result.requires_prior_auth is True
        assert result.matched_rule == RULE_CLAIM_POLICY_REFERENCE
        assert result.policy_reference == "POL-X"

    def test_unreferenced_claim_policy_id_is_not_enough(self):
        engine = PriorAuthRuleEngine(policy_records=[])
        result = engine.evaluate(
            _precheck_claim(procedures=("11111",), policy_id="POL-NOT-IN-CORPUS")
        )
        assert result.requires_prior_auth is False
        assert result.matched_rule == RULE_DEFAULT_NO_AUTH

    def test_benefit_rule_has_priority_over_corpus_rule(self):
        payer_context = {
            "plan_id": "PLAN-AETNA-001",
            "benefits": [
                {"benefit_id": "BEN-001", "benefit_category": "Orthopedics",
                 "authorization_requirement": True},
            ],
        }
        engine = PriorAuthRuleEngine(
            policy_records=[_policy_record("POL-CORPUS", ["27447"])]
        )
        result = engine.evaluate(
            _precheck_claim(procedures=("27447",), payer_context=payer_context)
        )
        assert result.requires_prior_auth is True
        assert result.matched_rule == RULE_BENEFIT_AUTHORIZATION

    def test_default_corpus_load_uses_real_normalized_policies(self):
        # Backed by the real V1 policy corpus (data/normalized).
        result = run_prior_auth_precheck(_precheck_claim(procedures=("33207",)))
        assert result.requires_prior_auth is True
        assert result.matched_rule == RULE_POLICY_CORPUS
        assert result.policy_reference == "NCD-20.8.3"
        assert result.source and "normalized_policies.json" in result.source

    def test_evaluation_is_deterministic(self):
        engine = PriorAuthRuleEngine(
            policy_records=[_policy_record("NCD-20.8.3", ["33206", "33207"])]
        )
        claim = _precheck_claim(procedures=("33207", "33206"))
        assert engine.evaluate(claim).to_dict() == engine.evaluate(claim).to_dict()

    def test_fail_closed_on_invalid_policy_records(self):
        result = run_prior_auth_precheck(
            _precheck_claim(procedures=("27447",)), policy_records=["garbage"]
        )
        assert result.requires_prior_auth is True
        assert result.matched_rule == RULE_FAIL_CLOSED
        assert result.source == "prior_auth_precheck:fail-closed"

    def test_result_is_explainable_and_immutable(self):
        result = PriorAuthPrecheckResult(
            requires_prior_auth=True,
            matched_rule=RULE_POLICY_CORPUS,
            reason="reason text",
            policy_reference="POL-X",
            source="unit",
        )
        assert set(result.to_dict()) == {
            "requires_prior_auth", "matched_rule", "reason",
            "policy_reference", "source",
        }
        # Audit detail must stay free of the control-plane ' | ' separator.
        assert " | " not in result.to_detail_line()
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.requires_prior_auth = False

    def test_engine_never_imports_llm_modules(self):
        import services.prior_auth_precheck as module

        import_lines = [
            line.strip()
            for line in inspect.getsource(module).splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        assert not any("llm" in line.lower() for line in import_lines)


# ---------------------------------------------------------------------------
# Control plane: explicit representation without touching the frozen machine
# ---------------------------------------------------------------------------

class TestControlPlanePrecheck:
    def _result(self, requires=True):
        return PriorAuthPrecheckResult(
            requires_prior_auth=requires,
            matched_rule=RULE_POLICY_CORPUS if requires else RULE_DEFAULT_NO_AUTH,
            reason="deterministic rule outcome",
            policy_reference="POL-X" if requires else None,
            source="unit",
        )

    def test_precheck_only_recordable_in_received(self):
        cp = WorkflowControlPlane()
        with pytest.raises(IllegalWorkflowTransition):
            cp.record_prior_auth_precheck("CLM-PC", self._result())  # INIT
        cp.transition("CLM-PC", ClaimWorkflowState.RECEIVED, "received")
        record = cp.record_prior_auth_precheck("CLM-PC", self._result(), claim_version=1)
        assert record.requires_prior_auth is True
        assert record.claim_version == 1
        cp.transition("CLM-PC", ClaimWorkflowState.EVALUATING, "evaluating")
        with pytest.raises(IllegalWorkflowTransition):
            cp.record_prior_auth_precheck("CLM-PC", self._result())

    def test_precheck_does_not_alter_states_or_event_trail(self):
        cp = WorkflowControlPlane()
        cp.transition("CLM-PC2", ClaimWorkflowState.RECEIVED, "received")
        trail_before = cp.events("CLM-PC2")
        cp.record_prior_auth_precheck("CLM-PC2", self._result(requires=False))
        # Frozen trail and state are untouched (no new transition invented).
        assert cp.events("CLM-PC2") == trail_before
        assert cp.current_state("CLM-PC2") == ClaimWorkflowState.RECEIVED

    def test_latest_precheck_is_exposed_and_frozen(self):
        cp = WorkflowControlPlane()
        cp.transition("CLM-PC3", ClaimWorkflowState.RECEIVED, "received")
        assert cp.prior_auth_precheck("CLM-PC3") is None
        first = cp.record_prior_auth_precheck("CLM-PC3", self._result(), claim_version=1)
        second = cp.record_prior_auth_precheck(
            "CLM-PC3", self._result(requires=False), claim_version=2
        )
        assert cp.prior_auth_precheck("CLM-PC3") is second
        assert first.precheck_id != second.precheck_id
        with pytest.raises(dataclasses.FrozenInstanceError):
            second.matched_rule = "tampered"


# ---------------------------------------------------------------------------
# Pipeline routing: auth-required and no-auth both stay on the frozen V1 path
# ---------------------------------------------------------------------------

class TestPipelineRoutingWithPrecheck:
    def test_requires_auth_routes_through_existing_authorization_path(self, pa_registry):
        chunks = [_chunk("POL-PA-REQ", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-PA-REQ", "POL-PA-REQ")
        pool = [_ev("ldl_report", "EV-PA-LDL", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"})]

        cp = WorkflowControlPlane()
        result = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source(pool), control_plane=cp
        )

        # Pre-check: corpus rule matches procedure 27447 -> PA required.
        assert result.prior_auth_precheck["requires_prior_auth"] is True
        assert result.prior_auth_precheck["matched_rule"] == RULE_POLICY_CORPUS
        assert result.prior_auth_precheck["policy_reference"] == "POL-PA-REQ"
        record = cp.prior_auth_precheck("CLM-PA-REQ")
        assert record is not None and record.requires_prior_auth is True
        assert record.claim_version == 1

        # Existing authorization/review path unchanged: RMI -> Agent2 recovery
        # -> resubmission -> Agent1 approval (frozen trail preserved exactly).
        assert result.final_outcome == DecisionOutcome.APPROVE
        assert result.agent2_invoked is True
        assert result.resubmissions == 1
        states = [event.state_after for event in cp.events("CLM-PA-REQ")]
        assert states == [
            "RECEIVED", "EVALUATING", "ROUTED_RECOVERY", "RECOVERING",
            "AWAITING_PROVIDER_DECISION", "RESUBMITTING", "EVALUATING", "APPROVED",
        ]
        # The pre-check is explicitly represented on the first EVALUATING event.
        evaluating = [e for e in cp.events("CLM-PA-REQ") if e.action == "Agent1 evaluating V1"][0]
        assert evaluating.detail.startswith("prior_auth_precheck: ")
        assert "requires_prior_auth=true" in evaluating.detail

    def test_no_auth_routes_directly_to_agent1_without_behavior_change(self, pa_registry):
        chunks = [_chunk("POL-PA-NONE", "C-ST", "At least 120 days of statin therapy.")]
        components = _build_components(chunks)
        claim = _scenario_claim(
            "CLM-PA-NONE", "POL-PA-NONE",
            evidence=[
                _ev("diagnosis", "EV-DX-1", {"verified_facts": True}),
                _ev("statin_trial", "EV-PA-ST", {"statin_duration_days": 150}),
            ],
            metrics_extra={"statin_duration_days": 150},
        )
        # Registry that does NOT require PA for this procedure/policy.
        registry = [_policy_record("POL-OTHER", ["99999"], payer="Aetna")]

        cp = WorkflowControlPlane()
        result = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source([]),
            control_plane=cp, prior_auth_registry=registry,
        )

        # Pre-check: no rule matched -> prior auth NOT required.
        assert result.prior_auth_precheck["requires_prior_auth"] is False
        assert result.prior_auth_precheck["matched_rule"] == RULE_DEFAULT_NO_AUTH
        assert result.prior_auth_precheck["policy_reference"] is None
        record = cp.prior_auth_precheck("CLM-PA-NONE")
        assert record is not None and record.requires_prior_auth is False

        # Direct Agent 1 V1 evaluation with no behavior change: direct APPROVE,
        # Agent 2 never invoked, frozen trail exactly as before Phase 1.
        assert result.final_outcome == DecisionOutcome.APPROVE
        assert result.agent2_invoked is False
        assert result.resubmissions == 0
        assert result.submissions == []
        states = [event.state_after for event in cp.events("CLM-PA-NONE")]
        assert states == ["RECEIVED", "EVALUATING", "APPROVED"]
        evaluating = [e for e in cp.events("CLM-PA-NONE") if e.action == "Agent1 evaluating V1"][0]
        assert "requires_prior_auth=false" in evaluating.detail

    def test_precheck_is_recorded_again_on_human_resolution_reentry(self, pa_registry):
        chunks = [_chunk("POL-PA-REQ", "C-LDL", "Documented LDL below 70 mg/dL required.")]
        components = _build_components(chunks)
        claim = _scenario_claim("CLM-PA-RE", "POL-PA-REQ")

        cp = WorkflowControlPlane()
        first = run_agent2_v1_pipeline(
            claim, components, recovery_source=_pool_source([]), control_plane=cp
        )
        assert first.final_outcome == DecisionOutcome.HUMAN_REVIEW
        assert first.prior_auth_precheck["requires_prior_auth"] is True

        # Human resolution re-enters NORMAL routing through RECEIVED; the
        # pre-check is deterministic and recorded again (now at version 2).
        resolved = reenter_after_human_resolution(
            claim, components, cp,
            attached_evidence=[
                _ev("ldl_report", "EV-PA-HUMAN", {"ldl_value": 55, "content_reference": "LDL 55 mg/dL"}),
            ],
            recovery_source=_pool_source([]),
            resolution_note="LDL report located in records.",
        )
        assert resolved.final_outcome == DecisionOutcome.APPROVE
        assert resolved.prior_auth_precheck["requires_prior_auth"] is True
        record = cp.prior_auth_precheck("CLM-PA-RE")
        assert record is not None and record.claim_version == 2
        assert cp.current_state("CLM-PA-RE") == ClaimWorkflowState.APPROVED


# ---------------------------------------------------------------------------
# API boundary: claim record exposes the pre-check additively
# ---------------------------------------------------------------------------

class TestApiPriorAuthContract:
    def test_claim_record_exposes_prior_auth_precheck(self, api_registry):
        client, _ = _make_client(_ldl_chunks(), _ldl_pool())
        claim = _scenario_claim("CLM-PA-API", "POL-API-LDL")

        created = client.post("/api/claims", json={"canonical_claim": claim})
        assert created.status_code == 201
        body = created.json()

        precheck = body["prior_auth_precheck"]
        assert precheck["requires_prior_auth"] is True
        assert precheck["matched_rule"] == RULE_POLICY_CORPUS
        assert precheck["policy_reference"] == "POL-API-LDL"
        assert precheck["reason"] and precheck["source"]

        # Frozen contract preserved: same routing, IDs and timeline shape.
        assert body["status"] == "ACCEPTED"
        assert body["workflow_state"] == "APPROVED"
        assert body["claim_version"] == 2
        assert body["evidence_request"]["correlation_id"] == "CORR-CLM-PA-API-V1"
        states = [e["state_after"] for e in body["timeline"]]
        assert states[0] == "RECEIVED" and states[-1] == "APPROVED"

        # GET returns the same record (persistence round-trip keeps the field).
        detail = client.get("/api/claims/CLM-PA-API").json()
        assert detail["prior_auth_precheck"] == precheck
