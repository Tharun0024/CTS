"""Phase 1 -- Agent1 decision contract tests.

Locks the stable structured decision contract exposed by Agent1:
  - final decision (outcome)
  - machine-readable reason_code
  - criterion results with evidence IDs/provenance
  - requested_information populated ONLY for REQUEST_MORE_INFORMATION
  - evidence-grounded rationale (reasoning + referenced evidence IDs)

And the frozen V1 routing semantics:
  - APPROVE -> terminal (agent2_recoverable False)
  - REQUEST_MORE_INFORMATION (missing/insufficient documentation) -> Agent2 recovery
  - hard coverage denial / exclusion -> REJECT terminal, Agent2 NEVER invoked
  - HUMAN_REVIEW -> terminal for Agent2 routing
  - no generic "REJECT -> Agent2" rule exists

PA003 corpus verification: PA003 (Neurology, chronic intractable migraine) has
payer membership but NO provider claim/evidence in the V1 databases, and the V1
policy corpus contains no migraine-treatment policy criteria (the only migraine
mention is CPB-0739, which explicitly deems migraine fMRI experimental).
Criteria must never be invented: the pipeline must fail closed to HUMAN_REVIEW.
"""

import json
from pathlib import Path

import pytest

from decision import (
    DecisionAgent,
    Policy,
    PolicyExclusion,
    PolicyCriterion,
    Rule,
    CaseData,
    EvidenceItem,
    EvidenceStatus,
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResponse,
)
from decision.decision_logic import make_decision


ROOT = Path(__file__).resolve().parent.parent


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def contract_policy() -> Policy:
    """Deterministic test policy (no LLM involvement)."""
    return Policy(
        policy_id="POL-CONTRACT",
        name="Contract Test Policy",
        exclusions=[
            PolicyExclusion(
                exclusion_id="EXC-DIAG",
                name="Excluded Diagnosis",
                rule=Rule(field="diagnoses", operator="contains", value="E10"),
            ),
        ],
        criteria=[
            PolicyCriterion(
                criterion_id="CRT-LAB",
                name="Lab Value Verification",
                description="Required lab value must be verified.",
                mandatory=True,
                required_evidence_keys=["lab_report"],
                clinical_rule=Rule(field="clinical_metrics.marker", operator="gt", value=8.0),
                evidence_rule=Rule(field="marker", operator="gt", value=8.0),
            ),
        ],
    )


def _verified_evidence(evidence_id="EV-LAB-001", marker=8.5):
    return EvidenceItem(
        evidence_key="lab_report",
        evidence_id=evidence_id,
        source="LabCorp",
        status=EvidenceStatus.VERIFIED,
        confidence_score=0.95,
        extracted_facts={"marker": marker},
    )


def _case(marker=8.5, diagnoses=None, payer="Aetna"):
    return CaseData(
        case_id="CASE-CONTRACT",
        patient_age=45,
        diagnoses=diagnoses or ["E11.9"],
        clinical_metrics={"marker": marker, "claim_payer": payer},
    )


# ── Contract: APPROVE ─────────────────────────────────────────────────────────

def test_approve_contract(contract_policy):
    resp = make_decision(contract_policy, _case(), [_verified_evidence()])

    assert resp.outcome == DecisionOutcome.APPROVE
    assert resp.reason_code == DecisionReasonCode.ALL_CRITERIA_SATISFIED
    assert resp.criteria_results["CRT-LAB"] is True
    # Terminal: never routed to Agent2
    assert resp.agent2_recoverable is False
    assert resp.requested_information == []
    # Evidence-grounded: real evidence IDs surface in contract
    assert resp.referenced_evidence_ids == ["EV-LAB-001"]
    evaluation = resp.criteria_evaluations["CRT-LAB"]
    assert evaluation.state == "PASS"
    provenance_ids = [p.evidence_id for p in evaluation.evidence_provenance]
    assert "EV-LAB-001" in provenance_ids
    assert resp.reasoning  # evidence-grounded rationale present


# ── Contract: hard criterion failure -> REJECT (terminal) ─────────────────────

def test_hard_criterion_failure_reject_is_terminal(contract_policy):
    # Marker present in data but fails the clinical rule -> definitive FAIL
    resp = make_decision(contract_policy, _case(marker=7.0), [_verified_evidence(marker=7.0)])

    assert resp.outcome == DecisionOutcome.REJECT
    assert resp.reason_code == DecisionReasonCode.CRITERION_FAILED_HARD
    assert resp.criteria_results["CRT-LAB"] is False
    # No generic REJECT -> Agent2 rule: hard denial is terminal
    assert resp.agent2_recoverable is False
    assert resp.requested_information == []
    assert resp.referenced_evidence_ids == ["EV-LAB-001"]


# ── Contract: coverage exclusion -> REJECT (terminal) ─────────────────────────

def test_coverage_exclusion_reject_is_terminal(contract_policy):
    resp = make_decision(contract_policy, _case(diagnoses=["E10"]), [_verified_evidence()])

    assert resp.outcome == DecisionOutcome.REJECT
    assert resp.reason_code == DecisionReasonCode.COVERAGE_EXCLUSION
    assert resp.exclusion_results["EXC-DIAG"] is True
    assert resp.agent2_recoverable is False
    assert resp.requested_information == []


# ── Contract: missing documentation -> REQUEST_MORE_INFORMATION -> Agent2 ─────

def test_missing_documentation_requests_information(contract_policy):
    case = CaseData(
        case_id="CASE-CONTRACT",
        patient_age=45,
        diagnoses=["E11.9"],
        # Marker absent from data: indeterminate clinical state -> MISSING,
        # never a fabricated FAIL.
        clinical_metrics={"claim_payer": "Aetna"},
    )
    resp = make_decision(contract_policy, case, evidence_list=[])

    assert resp.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
    assert resp.reason_code == DecisionReasonCode.MISSING_DOCUMENTATION
    # Policy-defined documentation request, grounded in the policy corpus of the case
    assert resp.requested_information == ["Lab Value Verification (CRT-LAB): lab_report"]
    # The ONLY outcome that routes to Agent2 recovery
    assert resp.agent2_recoverable is True
    assert resp.criteria_evaluations["CRT-LAB"].state == "MISSING"


# ── Contract: conflicting evidence -> HUMAN_REVIEW (terminal for Agent2) ──────

def test_conflicting_evidence_human_review_is_terminal(contract_policy):
    contradictory = EvidenceItem(
        evidence_key="lab_report",
        evidence_id="EV-LAB-002",
        source="External Lab",
        status=EvidenceStatus.CONTRADICTORY,
        confidence_score=0.9,
        extracted_facts={"marker": 3.0},
    )
    resp = make_decision(
        contract_policy, _case(), [_verified_evidence(), contradictory]
    )

    assert resp.outcome == DecisionOutcome.HUMAN_REVIEW
    assert resp.reason_code == DecisionReasonCode.EVIDENCE_CONFLICT
    assert resp.agent2_recoverable is False
    assert resp.requested_information == []
    # Both grounded evidence IDs remain traceable
    assert set(resp.referenced_evidence_ids) == {"EV-LAB-001", "EV-LAB-002"}


# ── Contract: unknown payer -> HUMAN_REVIEW (fail-closed) ─────────────────────

def test_unknown_payer_human_review_reason_code(contract_policy):
    resp = make_decision(contract_policy, _case(payer="UnknownPayer"), [_verified_evidence()])

    assert resp.outcome == DecisionOutcome.HUMAN_REVIEW
    assert resp.reason_code == DecisionReasonCode.UNKNOWN_PAYER
    assert resp.agent2_recoverable is False


# ── Routing semantics are structurally enforced on the schema ─────────────────

@pytest.mark.parametrize("outcome", [
    DecisionOutcome.APPROVE,
    DecisionOutcome.REJECT,
    DecisionOutcome.HUMAN_REVIEW,
])
def test_non_rmi_outcomes_cannot_be_agent2_recoverable(outcome):
    resp = DecisionResponse(
        case_id="CASE-X",
        outcome=outcome,
        agent2_recoverable=True,          # invalid attempt
        requested_information=["lab"],    # invalid attempt
    )
    assert resp.agent2_recoverable is False
    assert resp.requested_information == []


def test_rmi_outcome_may_carry_requested_information():
    resp = DecisionResponse(
        case_id="CASE-X",
        outcome=DecisionOutcome.REQUEST_MORE_INFORMATION,
        reason_code=DecisionReasonCode.MISSING_DOCUMENTATION,
        requested_information=["Lab Value Verification (CRT-LAB): lab_report"],
        agent2_recoverable=True,
    )
    assert resp.agent2_recoverable is True
    assert len(resp.requested_information) == 1


def test_decision_response_serializes_contract():
    resp = DecisionResponse(
        case_id="CASE-X",
        outcome=DecisionOutcome.REQUEST_MORE_INFORMATION,
        reason_code=DecisionReasonCode.MISSING_DOCUMENTATION,
        requested_information=["r1"],
        referenced_evidence_ids=["EV-1"],
        agent2_recoverable=True,
    )
    dumped = resp.model_dump(mode="json")
    assert dumped["outcome"] == "REQUEST_MORE_INFORMATION"
    assert dumped["reason_code"] == "MISSING_DOCUMENTATION"
    assert dumped["requested_information"] == ["r1"]
    assert dumped["referenced_evidence_ids"] == ["EV-1"]
    assert dumped["agent2_recoverable"] is True


# ── DecisionAgent-level contract (deterministic path, no LLM) ─────────────────

def test_decision_agent_exposes_contract_fields(contract_policy):
    agent = DecisionAgent(contract_policy)
    resp = agent.evaluate(_case(), [_verified_evidence()], use_llm=False)

    assert resp.outcome == DecisionOutcome.APPROVE
    assert resp.reason_code == DecisionReasonCode.ALL_CRITERIA_SATISFIED
    assert resp.referenced_evidence_ids == ["EV-LAB-001"]
    assert resp.agent2_recoverable is False


# ── PA003 verification against the REAL V1 corpus (no invented criteria) ──────

def test_pa003_has_no_provider_claim_in_v1_databases():
    from adapters.runtime_adapter import RuntimeAdapter

    adapter = RuntimeAdapter()
    assert adapter.get_provider_canonical_claim("PA003") is None
    assert adapter.get_linked_runtime_claim("PA003") is None
    # Payer context DOES exist (member is eligible) -- linkage alone must not
    # fabricate a provider claim or policy criteria.
    payer_ctx = adapter.get_payer_context("PA003")
    assert payer_ctx is not None
    assert payer_ctx.get("payer_id") == "Aetna"


def test_pa003_pipeline_fails_closed_without_invented_criteria():
    from services.integrated_pipeline import run_pipeline_from_db

    resp = run_pipeline_from_db("PA003", components={})

    assert resp.outcome == DecisionOutcome.HUMAN_REVIEW
    assert resp.reason_code == DecisionReasonCode.PROVIDER_CLAIM_NOT_FOUND
    # No criteria may be invented for a patient without a provider claim
    assert resp.criteria_results == {}
    assert resp.criteria_evaluations == {}
    assert resp.requested_information == []
    assert resp.agent2_recoverable is False
    assert resp.errors  # fail-closed reason surfaced


def test_pa003_clinical_domain_has_no_policy_criteria_in_v1_corpus():
    """PA003's active conditions are migraine/chronic-pain (Neurology). The V1
    corpus must not contain migraine-treatment criteria; CPB-0739 only mentions
    migraine to deem fMRI experimental. Nothing may be invented."""
    chunks = json.loads(
        (ROOT / "data" / "processed" / "chunks.json").read_text(encoding="utf-8")
    )
    keywords = ["migraine", "botulinum", "botox", "onabotulinum"]

    hits = [
        c for c in chunks
        if any(k in (c.get("text") or "").lower() for k in keywords)
    ]
    # Exactly one incidental mention: CPB-0739 fMRI policy, which EXCLUDES
    # migraine (experimental) rather than defining migraine treatment criteria.
    assert len(hits) == 1
    assert hits[0]["policy_id"] == "CPB-0739"
    assert "experimental" in hits[0]["text"].lower()
    # No corpus policy defines coverage criteria for PA003's conditions
    assert not any(
        c.get("policy_id") != "CPB-0739" for c in hits
    )
