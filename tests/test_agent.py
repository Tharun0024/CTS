import json
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
    CanonicalClaim,
    CriterionAssessmentStatus,
)
from decision.policy_evaluator import resolve_field_value, check_operator
from decision.llm_provider import MockLLMProvider, NVIDIAProvider
from decision.llm_schemas import LLMStructuredResponse, InterpretationState
from decision.llm_prompt import CRITERION_ASSESSMENT_SYSTEM_PROMPT, build_criterion_assessment_prompt


# Define a standard mock policy for testing
@pytest.fixture
def diabetes_policy() -> Policy:
    return Policy(
        policy_id="POL-001",
        name="Diabetes Care Eligibility Policy",
        exclusions=[
            PolicyExclusion(
                exclusion_id="EXC-AGE",
                name="Age Limit Exclusion",
                rule=Rule(field="patient_age", operator="gt", value=85),
            ),
            PolicyExclusion(
                exclusion_id="EXC-DIAG",
                name="Type 1 Diabetes Exclusion",
                rule=Rule(field="diagnoses", operator="contains", value="E10"),
            ),
        ],
        criteria=[
            PolicyCriterion(
                criterion_id="CRT-HBA1C",
                name="Elevated HbA1c Verification",
                description="Patient must have HbA1c above 8.0% verified by lab report.",
                mandatory=True,
                required_evidence_keys=["hba1c_report"],
                clinical_rule=Rule(field="clinical_metrics.HbA1c", operator="gt", value=8.0),
                evidence_rule=Rule(field="hba1c", operator="gt", value=8.0),
            ),
            PolicyCriterion(
                criterion_id="CRT-BP",
                name="Systolic Blood Pressure Check",
                description="Optional monitoring of blood pressure. Should be under 140 mmHg.",
                mandatory=False,
                required_evidence_keys=["bp_report"],
                clinical_rule=Rule(field="clinical_metrics.systolic_bp", operator="lt", value=140),
                evidence_rule=Rule(field="systolic_bp", operator="lt", value=140),
            ),
        ],
    )


def test_approve_flow_success(diabetes_policy):
    case_data = CaseData(
        case_id="CASE-001",
        patient_age=45,
        diagnoses=["E11.9"],  # Type 2 Diabetes
        clinical_metrics={"HbA1c": 8.5, "systolic_bp": 130},
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.VERIFIED,
            confidence_score=0.95,
            extracted_facts={"hba1c": 8.5},
        ),
        EvidenceItem(
            evidence_key="bp_report",
            source="Primary Care Office",
            status=EvidenceStatus.VERIFIED,
            confidence_score=0.90,
            extracted_facts={"systolic_bp": 130},
        ),
    ]

    agent = DecisionAgent(diabetes_policy)
    response = agent.evaluate(case_data, evidence)

    assert response.outcome == DecisionOutcome.APPROVE
    assert response.case_id == "CASE-001"
    assert response.exclusion_results["EXC-AGE"] is False
    assert response.exclusion_results["EXC-DIAG"] is False
    assert response.criteria_results["CRT-HBA1C"] is True
    assert response.criteria_results["CRT-BP"] is True
    assert response.evidence_status["hba1c_report"] == "verified"
    assert response.evidence_status["bp_report"] == "verified"
    assert any("All mandatory criteria are fully satisfied" in line for line in response.reasoning)


def test_approve_with_failing_optional_criterion(diabetes_policy):
    case_data = CaseData(
        case_id="CASE-002",
        patient_age=45,
        diagnoses=["E11.9"],
        clinical_metrics={"HbA1c": 8.5, "systolic_bp": 150},  # BP is 150 (violates systolic_bp < 140)
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.VERIFIED,
            confidence_score=0.95,
            extracted_facts={"hba1c": 8.5},
        ),
        EvidenceItem(
            evidence_key="bp_report",
            source="Primary Care Office",
            status=EvidenceStatus.VERIFIED,
            confidence_score=0.90,
            # violates evidence rule too
            extracted_facts={"systolic_bp": 150},
        ),
    ]

    agent = DecisionAgent(diabetes_policy)
    response = agent.evaluate(case_data, evidence)

    # Outcome should still be APPROVE because BP check is non-mandatory
    assert response.outcome == DecisionOutcome.APPROVE
    assert response.criteria_results["CRT-HBA1C"] is True
    assert response.criteria_results["CRT-BP"] is False
    assert any("Criterion 'Systolic Blood Pressure Check' (CRT-BP) is NOT satisfied" in line for line in response.reasoning)


def test_reject_by_age_exclusion(diabetes_policy):
    case_data = CaseData(
        case_id="CASE-003",
        patient_age=90,  # > 85, triggers EXC-AGE exclusion
        diagnoses=["E11.9"],
        clinical_metrics={"HbA1c": 8.5},
    )
    evidence = []

    agent = DecisionAgent(diabetes_policy)
    response = agent.evaluate(case_data, evidence)

    assert response.outcome == DecisionOutcome.REJECT
    assert response.exclusion_results["EXC-AGE"] is True
    assert any("Exclusion 'Age Limit Exclusion' (EXC-AGE) triggered" in line for line in response.reasoning)


def test_reject_by_diagnosis_exclusion(diabetes_policy):
    case_data = CaseData(
        case_id="CASE-004",
        patient_age=45,
        diagnoses=["E10.9"],  # contains E10 (Type 1), triggers EXC-DIAG exclusion
        clinical_metrics={"HbA1c": 8.5},
    )
    evidence = []

    agent = DecisionAgent(diabetes_policy)
    response = agent.evaluate(case_data, evidence)

    assert response.outcome == DecisionOutcome.REJECT
    assert response.exclusion_results["EXC-DIAG"] is True
    assert any("Exclusion 'Type 1 Diabetes Exclusion' (EXC-DIAG) triggered" in line for line in response.reasoning)


def test_reject_by_mandatory_clinical_violation(diabetes_policy):
    case_data = CaseData(
        case_id="CASE-005",
        # clinical HbA1c is 7.5 (failed HbA1c > 8.0)
        patient_age=45,
        clinical_metrics={"HbA1c": 7.5},
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.VERIFIED,
            confidence_score=0.95,
            extracted_facts={"hba1c": 7.5},
        )
    ]

    agent = DecisionAgent(diabetes_policy)
    response = agent.evaluate(case_data, evidence)

    assert response.outcome == DecisionOutcome.REJECT
    assert response.criteria_results["CRT-HBA1C"] is False
    assert any("clinical rule not met" in line for line in response.reasoning)
    assert any("Mandatory criterion 'Elevated HbA1c Verification' (CRT-HBA1C) was violated with high-confidence evidence" in line for line in response.reasoning)


def test_reject_by_mandatory_evidence_violation(diabetes_policy):
    case_data = CaseData(
        case_id="CASE-006",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5},  # clinical check says ok
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.VERIFIED,
            confidence_score=0.95,
            extracted_facts={"hba1c": 7.5},  # but evidence facts violate evidence_rule (hba1c > 8.0)
        )
    ]

    agent = DecisionAgent(diabetes_policy)
    response = agent.evaluate(case_data, evidence)

    assert response.outcome == DecisionOutcome.REJECT
    assert response.criteria_results["CRT-HBA1C"] is False
    assert any("extracted facts did not match validation rule" in line for line in response.reasoning)
    assert any("Mandatory criterion 'Elevated HbA1c Verification' (CRT-HBA1C) was violated with high-confidence evidence" in line for line in response.reasoning)


def test_human_review_contradictory_evidence(diabetes_policy):
    case_data = CaseData(
        case_id="CASE-007",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5},
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.CONTRADICTORY,  # Contradictory evidence
            confidence_score=0.95,
            extracted_facts={"hba1c": 8.5},
        )
    ]

    agent = DecisionAgent(diabetes_policy)
    response = agent.evaluate(case_data, evidence)

    assert response.outcome == DecisionOutcome.HUMAN_REVIEW
    assert response.evidence_status["hba1c_report"] == "contradictory"
    assert any("Evidence 'hba1c_report' for criterion 'Elevated HbA1c Verification' has status 'contradictory'" in line for line in response.reasoning)


def test_human_review_low_confidence(diabetes_policy):
    case_data = CaseData(
        case_id="CASE-008",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5},
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.VERIFIED,
            confidence_score=0.5,  # Below threshold 0.7
            extracted_facts={"hba1c": 8.5},
        )
    ]

    agent = DecisionAgent(diabetes_policy)
    response = agent.evaluate(case_data, evidence)

    assert response.outcome == DecisionOutcome.HUMAN_REVIEW
    assert response.evidence_status["hba1c_report"] == "low_confidence"
    assert any("has status 'low_confidence'" in line for line in response.reasoning)


def test_human_review_ambiguous(diabetes_policy):
    case_data = CaseData(
        case_id="CASE-009",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5},
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.VERIFIED,
            confidence_score=0.95,
            is_ambiguous=True,  # Ambiguous
            extracted_facts={"hba1c": 8.5},
        )
    ]

    agent = DecisionAgent(diabetes_policy)
    response = agent.evaluate(case_data, evidence)

    assert response.outcome == DecisionOutcome.HUMAN_REVIEW
    assert response.evidence_status["hba1c_report"] == "ambiguous"
    assert any("has status 'ambiguous'" in line for line in response.reasoning)


def test_request_more_information_missing_evidence(diabetes_policy):
    case_data = CaseData(
        case_id="CASE-010",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5},
    )
    evidence = []  # Missing required "hba1c_report"

    agent = DecisionAgent(diabetes_policy)
    response = agent.evaluate(case_data, evidence)

    assert response.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
    assert response.evidence_status["hba1c_report"] == "missing"
    assert any("Required evidence is missing: hba1c_report" in line for line in response.reasoning)


def test_field_resolution():
    # Helper direct test for field resolution
    class TempObj:
        def __init__(self):
            self.foo = "bar"
            self.nested = {"val": 42}

    obj = TempObj()

    assert resolve_field_value("foo", obj) == "bar"
    assert resolve_field_value("nested.val", obj) == 42
    assert resolve_field_value("nested.nonexistent", obj) is None
    assert resolve_field_value("nonexistent", obj) is None


def test_operators():
    # Test operators eq, ne, lt, lte, gt, gte, contains, not_contains, in, not_in
    assert check_operator(10, "eq", 10) is True
    assert check_operator(10, "eq", 5) is False
    assert check_operator(10, "ne", 5) is True

    assert check_operator(10, "lt", 15) is True
    assert check_operator(10, "lt", 10) is False
    assert check_operator(10, "lte", 10) is True

    assert check_operator(20, "gt", 15) is True
    assert check_operator(20, "gt", 20) is False
    assert check_operator(20, "gte", 20) is True

    assert check_operator(["A", "B"], "contains", "A") is True
    assert check_operator(["A", "B"], "contains", "C") is False
    assert check_operator(["A", "B"], "not_contains", "C") is True

    assert check_operator("A", "in", ["A", "B"]) is True
    assert check_operator("C", "in", ["A", "B"]) is False
    assert check_operator("C", "not_in", ["A", "B"]) is True

    # Type mismatches should fail gracefully
    assert check_operator(10, "lt", "string") is False
    assert check_operator(None, "lt", 5) is False
    assert check_operator(None, "eq", None) is True
    assert check_operator(10, "eq", None) is False


def test_new_safety_hardenings():
    # 1. Applicability Check (NOT_APPLICABLE state)
    policy_with_app = Policy(
        policy_id="POL-APP",
        name="Applicability Test Policy",
        criteria=[
            PolicyCriterion(
                criterion_id="CRT-APP",
                name="Hypertension Care",
                description="Blood pressure check for hypertension patients.",
                mandatory=True,
                applicability_rule=Rule(field="diagnoses", operator="contains", value="I10"),
                required_evidence_keys=["bp_report"],
                clinical_rule=Rule(field="clinical_metrics.systolic_bp", operator="lt", value=140),
            )
        ]
    )
    # Case doesn't have diagnose I10, so CRT-APP is NOT_APPLICABLE
    case_no_ht = CaseData(case_id="C-APP-1", patient_age=40, diagnoses=["E11"])
    agent = DecisionAgent(policy_with_app)
    res = agent.evaluate(case_no_ht, [])
    assert res.outcome == DecisionOutcome.APPROVE
    assert res.criteria_evaluations["CRT-APP"].state == "NOT_APPLICABLE"

    # Case has diagnose I10, so CRT-APP is applicable and missing evidence -> REQUEST_MORE_INFORMATION
    case_ht = CaseData(case_id="C-APP-2", patient_age=40, diagnoses=["I10.9"])
    res = agent.evaluate(case_ht, [])
    assert res.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
    assert res.criteria_evaluations["CRT-APP"].state == "MISSING"


def test_confidence_threshold_boundaries(diabetes_policy):
    case_data = CaseData(case_id="C-CONF", patient_age=40, clinical_metrics={"HbA1c": 8.5})
    
    # Boundary: EXACTLY on threshold (0.70) -> verified (outcome: APPROVE)
    ev_on = [EvidenceItem(evidence_key="hba1c_report", source="Lab", status=EvidenceStatus.VERIFIED, confidence_score=0.70, extracted_facts={"hba1c": 8.5})]
    agent = DecisionAgent(diabetes_policy)
    res = agent.evaluate(case_data, ev_on)
    assert res.outcome == DecisionOutcome.APPROVE
    assert res.criteria_evaluations["CRT-HBA1C"].state == "PASS"

    # Boundary: JUST below threshold (0.69) -> low_confidence (outcome: HUMAN_REVIEW)
    ev_below = [EvidenceItem(evidence_key="hba1c_report", source="Lab", status=EvidenceStatus.VERIFIED, confidence_score=0.69, extracted_facts={"hba1c": 8.5})]
    res = agent.evaluate(case_data, ev_below)
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert res.criteria_evaluations["CRT-HBA1C"].state == "CONFLICTING"


def test_missing_fields_and_invalid_types():
    assert resolve_field_value("clinical_metrics.non_existent", CaseData(case_id="C", patient_age=30)) is None
    # Compare string and int mathematically -> should fail safely (return False) instead of raising
    assert check_operator("hello", "lt", 10) is False
    assert check_operator(10, "gt", "hello") is False
    # Null comparisons
    assert check_operator(None, "gt", 5) is False
    assert check_operator(5, "lt", None) is False


def test_duplicate_evidence_contradiction(diabetes_policy):
    case_data = CaseData(case_id="C-DUPE", patient_age=40, clinical_metrics={"HbA1c": 8.5})
    # Two evidence items with conflicting facts
    evidence = [
        EvidenceItem(evidence_key="hba1c_report", source="Lab A", status=EvidenceStatus.VERIFIED, confidence_score=0.90, extracted_facts={"hba1c": 8.5}),
        EvidenceItem(evidence_key="hba1c_report", source="Lab B", status=EvidenceStatus.VERIFIED, confidence_score=0.90, extracted_facts={"hba1c": 7.2}),
    ]
    agent = DecisionAgent(diabetes_policy)
    res = agent.evaluate(case_data, evidence)
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert res.criteria_evaluations["CRT-HBA1C"].state == "CONFLICTING"
    assert res.evidence_status["hba1c_report"] == "contradictory"


def test_exclusion_uncertainty():
    exclusion_policy = Policy(
        policy_id="POL-EXC-UNC",
        name="Exclusion Uncertainty Policy",
        exclusions=[
            PolicyExclusion(
                exclusion_id="EXC-HEART",
                name="Severe Heart Failure",
                rule=Rule(field="clinical_metrics.heart_failure", operator="eq", value=True),
                required_evidence_keys=["cardio_report"]
            )
        ]
    )

    case_data = CaseData(case_id="C-EXC-UNC", patient_age=50, clinical_metrics={"heart_failure": True})
    agent = DecisionAgent(exclusion_policy)

    # 1. Verified exclusion -> REJECT
    ev_verified = [EvidenceItem(evidence_key="cardio_report", source="Clinic", status=EvidenceStatus.VERIFIED, confidence_score=0.9, extracted_facts={"heart_failure": True})]
    res = agent.evaluate(case_data, ev_verified)
    assert res.outcome == DecisionOutcome.REJECT

    # 2. Low-confidence exclusion -> HUMAN_REVIEW
    ev_low_conf = [EvidenceItem(evidence_key="cardio_report", source="Clinic", status=EvidenceStatus.VERIFIED, confidence_score=0.5, extracted_facts={"heart_failure": True})]
    res = agent.evaluate(case_data, ev_low_conf)
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW

    # 3. Contradictory exclusion -> HUMAN_REVIEW
    ev_contra = [EvidenceItem(evidence_key="cardio_report", source="Clinic", status=EvidenceStatus.CONTRADICTORY, confidence_score=0.9, extracted_facts={"heart_failure": True})]
    res = agent.evaluate(case_data, ev_contra)
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW

    # 4. Unverified exclusion -> HUMAN_REVIEW
    ev_unverified = [EvidenceItem(evidence_key="cardio_report", source="Clinic", status=EvidenceStatus.UNVERIFIED, confidence_score=0.9, extracted_facts={"heart_failure": True})]
    res = agent.evaluate(case_data, ev_unverified)
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW


def test_mandatory_criterion_uncertainty(diabetes_policy):
    # Clinic HbA1c is 7.5 (failed HbA1c > 8.0)
    case_data = CaseData(case_id="C-MAND-UNC", patient_age=40, clinical_metrics={"HbA1c": 7.5})

    # 1. Verified mandatory violation -> REJECT
    ev_ver = [EvidenceItem(evidence_key="hba1c_report", source="Lab", status=EvidenceStatus.VERIFIED, confidence_score=0.9, extracted_facts={"hba1c": 7.5})]
    agent = DecisionAgent(diabetes_policy)
    res = agent.evaluate(case_data, ev_ver)
    assert res.outcome == DecisionOutcome.REJECT

    # 2. Low-confidence mandatory violation -> HUMAN_REVIEW
    # V1 hierarchy: CONFLICT (evidence quality issue) outranks FAILED clinical rule.
    ev_low_conf = [EvidenceItem(evidence_key="hba1c_report", source="Lab", status=EvidenceStatus.VERIFIED, confidence_score=0.5, extracted_facts={"hba1c": 7.5})]
    res = agent.evaluate(case_data, ev_low_conf)
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW

    # 3. Contradictory mandatory violation -> HUMAN_REVIEW
    ev_contra = [EvidenceItem(evidence_key="hba1c_report", source="Lab", status=EvidenceStatus.CONTRADICTORY, confidence_score=0.9, extracted_facts={"hba1c": 7.5})]
    res = agent.evaluate(case_data, ev_contra)
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW

    # 4. Unverified mandatory violation -> HUMAN_REVIEW
    ev_unverified = [EvidenceItem(evidence_key="hba1c_report", source="Lab", status=EvidenceStatus.UNVERIFIED, confidence_score=0.9, extracted_facts={"hba1c": 7.5})]
    res = agent.evaluate(case_data, ev_unverified)
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW


def test_multiple_simultaneous_problems(diabetes_policy):
    case_data = CaseData(case_id="C-MULTI-ERR", patient_age=45, clinical_metrics={"HbA1c": 8.5})
    # Optional evidence is missing (bp_report) -> missing
    # Mandatory evidence is low confidence (hba1c_report) -> low_confidence / conflict
    evidence = [EvidenceItem(evidence_key="hba1c_report", source="Lab", status=EvidenceStatus.VERIFIED, confidence_score=0.5, extracted_facts={"hba1c": 8.5})]
    agent = DecisionAgent(diabetes_policy)
    res = agent.evaluate(case_data, evidence)
    # The mandatory criteria has conflict (due to low confidence score). Conflict takes hierarchy precedence!
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW


def test_icd_prefix_matching():
    # Safe ICD code matches check
    policy_icd = Policy(
        policy_id="POL-ICD",
        name="ICD Matching Policy",
        exclusions=[],
        criteria=[
            PolicyCriterion(
                criterion_id="CRT-ICD",
                name="Diabetic Diagnoses",
                description="Checks for active E10 category.",
                mandatory=True,
                clinical_rule=Rule(field="diagnoses", operator="contains", value="E10")
            )
        ]
    )

    agent = DecisionAgent(policy_icd)
    
    # E10.9 contains E10 category -> matches (APPROVE)
    c1 = CaseData(case_id="C1", patient_age=40, diagnoses=["E10.9"])
    assert agent.evaluate(c1, []).outcome == DecisionOutcome.APPROVE

    # E10 exactly matches E10 category -> matches (APPROVE)
    c2 = CaseData(case_id="C2", patient_age=40, diagnoses=["E10"])
    assert agent.evaluate(c2, []).outcome == DecisionOutcome.APPROVE

    # E100 contains "E10" as substring, but represents a different code category -> must NOT match (REJECT / FAIL)
    c3 = CaseData(case_id="C3", patient_age=40, diagnoses=["E100"])
    assert agent.evaluate(c3, []).outcome == DecisionOutcome.REJECT
    
    # E11 does not contain E10 -> fails (REJECT)
    c4 = CaseData(case_id="C4", patient_age=40, diagnoses=["E11.9"])
    assert agent.evaluate(c4, []).outcome == DecisionOutcome.REJECT


def test_invalid_policy_rules_handling():
    # Rule with invalid/unsupported operator
    bad_policy = Policy(
        policy_id="POL-BAD",
        name="Invalid Policy",
        exclusions=[
            PolicyExclusion(
                exclusion_id="EXC-BAD",
                name="Unsupported Comparison",
                rule=Rule(field="patient_age", operator="unsupported_op", value=50)
            )
        ]
    )
    case_data = CaseData(case_id="C-BAD", patient_age=45)
    agent = DecisionAgent(bad_policy)
    res = agent.evaluate(case_data, [])
    # Fail closed! Leads to HUMAN_REVIEW
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert len(res.errors) > 0
    assert any("Policy validation failed" in log for log in res.reasoning)


def test_empty_boundary_conditions():
    # 1. Empty criteria list policy
    empty_policy = Policy(policy_id="POL-EMPTY", name="Empty Policy", exclusions=[], criteria=[])
    case_data = CaseData(case_id="C-EMPTY", patient_age=45)
    agent = DecisionAgent(empty_policy)
    # No exclusions triggered, no mandatory criteria failed -> APPROVED
    assert agent.evaluate(case_data, []).outcome == DecisionOutcome.APPROVE

    # 2. Empty evidence list matches
    policy_evidence_req = Policy(
        policy_id="POL-EV-REQ",
        name="Evidence Required Policy",
        criteria=[
            PolicyCriterion(
                criterion_id="CRT-EV-REQ",
                name="Verification",
                description="Needs verification",
                mandatory=True,
                required_evidence_keys=["req_doc"]
            )
        ]
    )
    agent_ev = DecisionAgent(policy_evidence_req)
    res = agent_ev.evaluate(case_data, [])
    assert res.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
    assert res.criteria_evaluations["CRT-EV-REQ"].state == "MISSING"


def test_multiple_simultaneous_exclusions_and_failures(diabetes_policy):
    # 1. Multiple exclusions triggered
    case_data_excs = CaseData(
        case_id="CASE-MULT-EXC",
        patient_age=95,  # triggers EXC-AGE (age limit)
        diagnoses=["E10"],  # triggers EXC-DIAG (Type 1)
        clinical_metrics={"HbA1c": 8.5},
    )
    agent = DecisionAgent(diabetes_policy)
    res = agent.evaluate(case_data_excs, [])
    assert res.outcome == DecisionOutcome.REJECT
    assert res.exclusion_results["EXC-AGE"] is True
    assert res.exclusion_results["EXC-DIAG"] is True

    # 2. Multiple mandatory criteria failures
    multi_criteria_policy = Policy(
        policy_id="POL-MULT-CRIT",
        name="Multi Criteria Policy",
        criteria=[
            PolicyCriterion(
                criterion_id="CRT-1",
                name="Crit 1",
                description="desc 1",
                mandatory=True,
                clinical_rule=Rule(field="clinical_metrics.val1", operator="gt", value=10)
            ),
            PolicyCriterion(
                criterion_id="CRT-2",
                name="Crit 2",
                description="desc 2",
                mandatory=True,
                clinical_rule=Rule(field="clinical_metrics.val2", operator="gt", value=20)
            )
        ]
    )

    case_data_fails = CaseData(
        case_id="CASE-MULT-FAIL",
        patient_age=30,
        clinical_metrics={"val1": 5, "val2": 15}  # both fail
    )
    agent_mult = DecisionAgent(multi_criteria_policy)
    res_mult = agent_mult.evaluate(case_data_fails, [])
    assert res_mult.outcome == DecisionOutcome.REJECT
    assert res_mult.criteria_evaluations["CRT-1"].state == "FAIL"
    assert res_mult.criteria_evaluations["CRT-2"].state == "FAIL"


# =====================================================================
# PHASE 2 - LLM INTELLIGENCE LAYER TESTS (17 Requirements covered)
# =====================================================================

def test_llm_successful_clinical_and_multiple_fact_extraction(diabetes_policy):
    # Tests:
    # 1. Successful clinical fact extraction
    # 2. Multiple fact extraction
    # 13. LLM output correctly entering the existing evidence evaluator
    # 14. LLM interpretation followed by deterministic APPROVE
    case_data = CaseData(
        case_id="C-INT-SUCCESS",
        patient_age=45,
        diagnoses=["E11.9"],
        clinical_metrics={"HbA1c": 8.5, "systolic_bp": 125}
    )
    # Evidence contains raw texts to be analyzed
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.4,
            unstructured_text="The HbA1c is currently 8.5%."
        ),
        EvidenceItem(
            evidence_key="bp_report",
            source="Heart Clinic",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.4,
            unstructured_text="Wait! Systolic BP is 125."
        )
    ]

    mock_resp = {
        "extracted_facts": [
            {
                "evidence_key": "hba1c_report",
                "source": "LabCorp",
                "original_text": "HbA1c is currently 8.5%",
                "extracted_fact": {"hba1c": 8.5},
                "confidence": 0.95,
                "state": "SUPPORTED",
                "interpretation_status": "verified",
                "reasoning": "Extracted HbA1c successfully."
            },
            {
                "evidence_key": "bp_report",
                "source": "Heart Clinic",
                "original_text": "Systolic BP is 125",
                "extracted_fact": {"systolic_bp": 125},
                "confidence": 0.92,
                "state": "SUPPORTED",
                "interpretation_status": "verified",
                "reasoning": "Extracted BP successfully."
            }
        ],
        "criterion_interpretations": [
            {
                "criterion_id": "CRT-HBA1C",
                "state": "SUPPORTED",
                "supporting_evidence_ids": [],
                "contradictory_evidence_ids": [],
                "confidence": 0.95,
                "reasoning_summary": "HbA1c is above 8.0."
            }
        ],
        "overall_reasoning_summary": "Extracted medical indicators match requirements."
    }

    mock_provider = MockLLMProvider(response_generator=lambda p, s: json.dumps(mock_resp))
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    
    # RUN
    res = agent.evaluate(case_data, evidence, use_llm=True)
    
    assert res.outcome == DecisionOutcome.APPROVE
    # Check that evidence got updated
    assert evidence[0].extracted_facts["hba1c"] == 8.5
    assert evidence[0].status == EvidenceStatus.VERIFIED
    assert evidence[0].confidence_score == 0.95
    assert evidence[1].extracted_facts["systolic_bp"] == 125
    assert evidence[1].status == EvidenceStatus.VERIFIED
    assert evidence[1].confidence_score == 0.92


def test_llm_interpretation_deterministic_reject(diabetes_policy):
    # Tests:
    # 15. LLM interpretation followed by deterministic REJECT (violation of mandatory value)
    case_data = CaseData(
        case_id="C-INT-REJECT",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5}
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.4,
            unstructured_text="The patient's lab value of HbA1c is 7.1%"
        )
    ]

    mock_resp = {
        "extracted_facts": [
            {
                "evidence_key": "hba1c_report",
                "original_text": "HbA1c is 7.1%",
                "source": "LabCorp",
                "extracted_fact": {"hba1c": 7.1},
                "confidence": 0.95,
                "state": "SUPPORTED",
                "interpretation_status": "verified",
                "reasoning": "Extracted flat value."
            }
        ],
        "criterion_interpretations": [],
        "overall_reasoning_summary": "Extracted facts."
    }

    mock_provider = MockLLMProvider(response_generator=lambda p, s: json.dumps(mock_resp))
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)
    
    # Should REJECT because mandatory criterion requires hba1c > 8.0, but extracted is 7.1.
    assert res.outcome == DecisionOutcome.REJECT
    assert res.criteria_evaluations["CRT-HBA1C"].state == "FAIL"


def test_llm_interpretation_missing_evidence(diabetes_policy):
    # Tests:
    # 3. Missing information
    # 16. LLM interpretation resulting in REQUEST_MORE_INFORMATION
    case_data = CaseData(
        case_id="C-INT-MISSING",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5}
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.4,
            unstructured_text="Doctor notes did not attach HbA1c report."
        )
    ]

    # LLM explicitly sets interpretation_status to unverified/missing and state = MISSING
    mock_resp = {
        "extracted_facts": [
            {
                "evidence_key": "hba1c_report",
                "original_text": "No report uploaded",
                "source": "LabCorp",
                "extracted_fact": {},
                "confidence": 0.9,
                "state": "MISSING",
                "interpretation_status": "unverified",
                "reasoning": "Report is missing"
            }
        ],
        "criterion_interpretations": [],
        "overall_reasoning_summary": "Critical facts missing."
    }

    mock_provider = MockLLMProvider(response_generator=lambda p, s: json.dumps(mock_resp))
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)
    
    assert res.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
    assert res.criteria_evaluations["CRT-HBA1C"].state == "MISSING"


def test_llm_ambiguous_and_contradictory_evidence(diabetes_policy):
    # Tests:
    # 4. Ambiguous clinical statement
    # 5. Contradictory evidence
    # 17. LLM interpretation resulting in HUMAN_REVIEW
    case_data = CaseData(
        case_id="C-INT-AMB",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5}
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.4,
            unstructured_text="Patient stated they had a recent HbA1c between 7.5% and 8.5%."
        )
    ]

    # LLM reports ambiguity
    mock_resp = {
        "extracted_facts": [
            {
                "evidence_key": "hba1c_report",
                "original_text": "7.5% and 8.5%",
                "source": "LabCorp",
                "extracted_fact": {"hba1c": 8.0},
                "confidence": 0.8,
                "state": "UNCERTAIN",
                "interpretation_status": "unverified",
                "reasoning": "Unstructured value represents clear patient uncertainty."
            }
        ],
        "criterion_interpretations": [],
        "overall_reasoning_summary": "Text contains high ambiguity."
    }

    mock_provider = MockLLMProvider(response_generator=lambda p, s: json.dumps(mock_resp))
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)

    # UNCERTAIN mapping forces is_ambiguous=True in evidence item, leading to HUMAN_REVIEW
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert res.criteria_evaluations["CRT-HBA1C"].state == "CONFLICTING"


def test_llm_low_confidence_interpretation(diabetes_policy):
    # Tests:
    # 6. Low-confidence interpretation
    case_data = CaseData(
        case_id="C-INT-CONF",
        patient_age=45,
        clinical_metrics={"HbA1c": 9.0}
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.4,
            unstructured_text="HbA1c seems to be 9.0"
        )
    ]

    mock_resp = {
        "extracted_facts": [
            {
                "evidence_key": "hba1c_report",
                "original_text": "seems to be 9.0",
                "source": "Lab",
                "extracted_fact": {"hba1c": 9.0},
                "confidence": 0.5, # Below default 0.70 threshold
                "state": "SUPPORTED",
                "interpretation_status": "verified",
                "reasoning": "Marginal confidence from phrasing."
            }
        ],
        "overall_reasoning_summary": "Low confidence."
    }

    mock_provider = MockLLMProvider(response_generator=lambda p, s: json.dumps(mock_resp))
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)
    
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert res.evidence_status["hba1c_report"] == "low_confidence"


def test_llm_unsupported_claim(diabetes_policy):
    # Tests:
    # 7. Unsupported claim
    case_data = CaseData(
        case_id="C-UNSUPP",
        patient_age=45,
        clinical_metrics={"HbA1c": 9.0}
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.5,
            unstructured_text="The documentation explicitly states hba1c test was rejected."
        )
    ]

    mock_resp = {
        "extracted_facts": [
            {
                "evidence_key": "hba1c_report",
                "original_text": "hba1c test was rejected",
                "source": "Lab",
                "extracted_fact": {},
                "confidence": 0.9,
                "state": "UNSUPPORTED",
                "interpretation_status": "unverified",
                "reasoning": "Claim unsupported."
            }
        ],
        "overall_reasoning_summary": "No verified metrics."
    }

    mock_provider = MockLLMProvider(response_generator=lambda p, s: json.dumps(mock_resp))
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)
    
    # UNSUPPORTED -> state is CONFLICTING/unverified in final evaluation, outcome is HUMAN_REVIEW
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW


def test_llm_malformed_json_fallback(diabetes_policy):
    # Tests:
    # 8. Malformed LLM JSON
    case_data = CaseData(case_id="C-JSON-ERR", patient_age=45)
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.5,
            unstructured_text="..."
        )
    ]

    # Return raw text that is not JSON
    mock_provider = MockLLMProvider(response_generator=lambda p, s: "This is not JSON!")
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)
    
    # Must fail safely to HUMAN_REVIEW
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert any("LLM Layer failed" in err for err in res.errors)


def test_llm_invalid_structured_response_fallback(diabetes_policy):
    # Tests:
    # 9. Invalid structured response (schema validation fails because of missing confidence/facts fields)
    case_data = CaseData(case_id="C-SCHEMA-ERR", patient_age=45)
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.5,
            unstructured_text="..."
        )
    ]

    # Missing mandatory "confidence" and "state" fields inside extracted_facts list
    bad_resp = {
        "extracted_facts": [
            {
                "evidence_key": "hba1c_report",
                "source": "Lab",
                "original_text": "...",
                "extracted_fact": {},
                # confidence is missing!
                "interpretation_status": "verified",
                "reasoning": "Missing confidence"
            }
        ],
        "overall_reasoning_summary": "Bad payload schema."
    }

    mock_provider = MockLLMProvider(response_generator=lambda p, s: json.dumps(bad_resp))
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)

    # Must fail safely to HUMAN_REVIEW
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert len(res.errors) > 0


def test_llm_api_failure_handling(diabetes_policy):
    # Tests:
    # 10. NVIDIA API failure
    case_data = CaseData(case_id="C-API-ERR", patient_age=45)
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.5,
            unstructured_text="..."
        )
    ]

    def trigger_failure(p, s):
        raise IOError("Connection timeout from NVIDIA API microservice.")

    mock_provider = MockLLMProvider(response_generator=trigger_failure)
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)

    # Must fail safely to HUMAN_REVIEW
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert any("Connection timeout" in err for err in res.errors)


def test_llm_missing_api_key(diabetes_policy):
    # Tests:
    # 11. Missing API key (ensures it is flagged safely)
    case_data = CaseData(
        case_id="C-KEY-ERR",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5}
    )
    # Supply unstructured evidence status to trigger provider flow
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.5,
            unstructured_text="HbA1c testing has been performed."
        )
    ]
    
    # Construct NVIDIAProvider with blank key explicitly to trigger missing key error
    provider = NVIDIAProvider(api_key="")
    agent = DecisionAgent(diabetes_policy, llm_provider=provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)

    # Must fail safely to HUMAN_REVIEW
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert any("API Key is missing" in err for err in res.errors)


def test_llm_unsupported_facts_are_ignored(diabetes_policy):
    # Tests:
    # 12. LLM attempts to introduce unsupported facts
    case_data = CaseData(
        case_id="C-UNSUPPORTED-FACTS",
        patient_age=45,
        clinical_metrics={"HbA1c": 9.0}
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.5,
            unstructured_text="HbA1c report is 9.0"
        )
    ]

    mock_resp = {
        "extracted_facts": [
            {
                "evidence_key": "hba1c_report",
                "source": "Lab",
                "original_text": "HbA1c report is 9.0",
                # Attempts to introduce arbitrary claims/factors not part of policy rules
                "extracted_fact": {
                    "hba1c": 9.0,
                    "patient_blood_type": "O-Positive",
                    "patient_favorite_color": "Blue"
                },
                "confidence": 0.95,
                "state": "SUPPORTED",
                "interpretation_status": "verified",
                "reasoning": "Extracted extra facts"
            }
        ],
        "overall_reasoning_summary": "Extracted facts."
    }

    mock_provider = MockLLMProvider(response_generator=lambda p, s: json.dumps(mock_resp))
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)

    # Outcome should be APPROVE (hba1c passes). The unsupported fields are simply ignored by deterministic rules.
    assert res.outcome == DecisionOutcome.APPROVE
    assert evidence[0].extracted_facts["patient_favorite_color"] == "Blue"


# =====================================================================
# PHASE 3 - LLM EFFICIENCY, RETRIES, AND SECURITY ACTION TESTS
# =====================================================================

def test_nvidia_config_and_model(monkeypatch):
    """
    Validates model settings (z-ai/glm-5.2) and URL formatting suffixes.
    """
    import decision.llm_provider
    monkeypatch.setattr(decision.llm_provider, "load_env", lambda: None)
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)
    provider = NVIDIAProvider(api_key="mock_key")
    # Verify default model is z-ai/glm-5.2
    assert provider.model == "z-ai/glm-5.2"
    # Verify path endpoint resolution appending chat completion suffix
    assert provider.endpoint == "https://integrate.api.nvidia.com/v1/chat/completions"

    # Verify custom full completions end path remains clean
    provider2 = NVIDIAProvider(
        api_key="mock_key",
        base_url="https://override.com/chat/completions"
    )
    assert provider2.endpoint == "https://override.com/chat/completions"


def test_llm_retry_on_transient_failure(diabetes_policy):
    """
    Verifies that the LLM agent handles exactly ONE retry on transient/malformed exceptions.
    Succeds on attempt 2.
    """
    case_data = CaseData(
        case_id="C-RETRY-SUCCESS",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5}
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.5,
            unstructured_text="HbA1c is 8.5"
        )
    ]

    calls = 0
    def generator_fail_once(p, s):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise IOError("Simulated transient 502 Bad Gateway")
        return json.dumps({
            "extracted_facts": [
                {
                    "evidence_key": "hba1c_report",
                    "source": "Lab",
                    "original_text": "HbA1c is 8.5",
                    "extracted_fact": {"hba1c": 8.5},
                    "confidence": 0.95,
                    "state": "SUPPORTED",
                    "interpretation_status": "verified",
                    "reasoning": "Extracted on attempt 2"
                }
            ],
            "overall_reasoning_summary": "Recovered on attempt 2."
        })

    mock_provider = MockLLMProvider(response_generator=generator_fail_once)
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)

    assert res.outcome == DecisionOutcome.APPROVE
    assert mock_provider.call_count == 2
    assert any("Transient/Malformed LLM exception on attempt 1" in r for r in res.reasoning)


def test_llm_persistent_failure_fails_closed(diabetes_policy):
    """
    Registers a persistent provider failure (after retrying) and ensures it fails closed.
    """
    case_data = CaseData(
        case_id="C-RETRY-FAIL",
        patient_age=45,
        clinical_metrics={"HbA1c": 8.5}
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.5,
            unstructured_text="HbA1c is 8.5"
        )
    ]

    def generator_always_fail(p, s):
        raise IOError("Persistent offline error")

    mock_provider = MockLLMProvider(response_generator=generator_always_fail)
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)

    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    # Verify it only tried twice (initial + exactly one retry)
    assert mock_provider.call_count == 2


def test_llm_unnecessary_call_avoidance(diabetes_policy):
    """
    Verifies that the LLM call is avoided entirely when:
    1. Deterministic features are already sufficient (yields APPROVE/REJECT).
    2. No unstructured text is present.
    """
    # Test Scenario 1: Case already satisfies Approve deterministically.
    case_data_ok = CaseData(
        case_id="C-SUFFICIENT",
        patient_age=40,
        diagnoses=["E11.9"],
        clinical_metrics={"HbA1c": 8.5, "systolic_bp": 130}
    )
    evidence_ok = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.VERIFIED,
            confidence_score=0.9,
            extracted_facts={"hba1c": 8.5}
        )
    ]

    mock_provider = MockLLMProvider()
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data_ok, evidence_ok, use_llm=True)

    assert res.outcome == DecisionOutcome.APPROVE
    # LLM is avoided because deterministic check is already sufficient!
    assert mock_provider.call_count == 0

    # Test Scenario 2: No unstructured text fields in evidence list.
    case_data_unverified = CaseData(
        case_id="C-UNVERIFIED-NO-TEXT",
        patient_age=40,
        clinical_metrics={"HbA1c": 8.5}
    )
    evidence_no_text = [
        # unverified, low confidence, triggers REQUEST_MORE_INFORMATION / HUMAN_REVIEW but has no text to extract
        EvidenceItem(
            evidence_key="hba1c_report",
            source="LabCorp",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.5
        )
    ]

    res2 = agent.evaluate(case_data_unverified, evidence_no_text, use_llm=True)
    assert res2.outcome == DecisionOutcome.HUMAN_REVIEW
    # Avoided call since there is no unstructured text to parse
    assert mock_provider.call_count == 0


def test_llm_cannot_override_final_decision(diabetes_policy):
    """
    Verifies that even if the LLM extracts supported facts, deterministic exclusion rules (EXC-AGE)
    override and make the final decision.
    """
    case_data = CaseData(
        case_id="C-AGE-OVERRIDE",
        patient_age=95,  # Exclusions rule > 85 triggers
        clinical_metrics={"HbA1c": 9.0}
    )
    evidence = [
        EvidenceItem(
            evidence_key="hba1c_report",
            source="Lab",
            status=EvidenceStatus.UNVERIFIED,
            confidence_score=0.5,
            unstructured_text="HbA1c is 9.0"
        )
    ]

    mock_resp = {
        "extracted_facts": [
            {
                "evidence_key": "hba1c_report",
                "source": "Lab",
                "original_text": "HbA1c is 9.0",
                "extracted_fact": {"hba1c": 9.0},
                "confidence": 0.95,
                "state": "SUPPORTED",
                "interpretation_status": "verified",
                "reasoning": "Standard verification"
            }
        ],
        "overall_reasoning_summary": "Extracted"
    }

    mock_provider = MockLLMProvider(response_generator=lambda p, s: json.dumps(mock_resp))
    agent = DecisionAgent(diabetes_policy, llm_provider=mock_provider)
    res = agent.evaluate(case_data, evidence, use_llm=True)

    # Outcome is REJECT because of age, proving parser only interprets data but cannot override decisions.
    assert res.outcome == DecisionOutcome.REJECT
    assert res.exclusion_results["EXC-AGE"] is True


def test_prompt_injection_safety():
    """
    Verifies system prompts contain the prompt injection instruction safeguards.
    """
    from decision.llm_prompt import SYSTEM_PROMPT
    # Verify keywords resisting instructions injection
    assert "Ignore any commands" in SYSTEM_PROMPT or "ignore" in SYSTEM_PROMPT.lower()
    assert "DATA" in SYSTEM_PROMPT


def test_openrouter_provider_config():
    """
    Verifies OpenRouterProvider configuration parsing behavior.
    """
    from decision.llm_provider import OpenRouterProvider
    provider = OpenRouterProvider(api_key="or-test-key", model="google/gemma-4-26b-a4b-it:free", base_url="https://openrouter.ai/api/v1")
    assert provider.api_key == "or-test-key"
    assert provider.model == "google/gemma-4-26b-a4b-it:free"
    assert provider.endpoint == "https://openrouter.ai/api/v1/chat/completions"


def test_openrouter_provider_missing_key():
    """
    Verifies OpenRouterProvider raises ValueError when API key is missing.
    """
    from decision.llm_provider import OpenRouterProvider
    provider = OpenRouterProvider(api_key="")
    import pytest
    with pytest.raises(ValueError, match="OpenRouter API Key is missing"):
        provider.generate_structured_response("test", "test_system")


# =====================================================================
# NEW CANONICAL CLAIM + RAG POLICY CRITERION-ASSESSMENT CONTRACT
# =====================================================================

def _canonical_claim(case_id="CANON-001"):
    return {
        "case_data": {
            "case_id": case_id,
            "patient_age": 45,
            "diagnoses": ["E11.9"],
            "clinical_metrics": {"HbA1c": 8.5, "systolic_bp": 130},
        },
        "evidence": [
            {
                "evidence_key": "hba1c_report",
                "source": "Canonical Lab",
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {"hba1c": 8.5},
            },
            {
                "evidence_key": "bp_report",
                "source": "Canonical Clinic",
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {"systolic_bp": 130},
            },
        ],
    }


def _criterion_assessment_response(hba1c_status="SATISFIED"):
    return {
        "criterion_assessments": [
            {
                "criterion_id": "CRT-HBA1C",
                "status": hba1c_status,
                "evidence_paths": ["$.evidence[0].extracted_facts.hba1c"],
                "reasoning": "The canonical lab fact is available at the cited path.",
            },
            {
                "criterion_id": "CRT-BP",
                "status": "SATISFIED",
                "evidence_paths": ["$.evidence[1].extracted_facts.systolic_bp"],
                "reasoning": "The canonical vital-sign fact is available at the cited path.",
            },
        ]
    }


def _single_criterion_response(prompt, hba1c_status="SATISFIED", path_override=None):
    criterion_id = json.loads(prompt)["rag_criterion"]["criterion_id"]
    is_hba1c = criterion_id == "CRT-HBA1C"
    path = path_override or (
        "$.evidence[0].extracted_facts.hba1c"
        if is_hba1c
        else "$.evidence[1].extracted_facts.systolic_bp"
    )
    return json.dumps(
        {
            "criterion_assessments": [
                {
                    "criterion_id": criterion_id,
                    "status": hba1c_status if is_hba1c else "SATISFIED",
                    "evidence_paths": [path],
                    "reasoning": "Assessment is grounded in the cited canonical path.",
                }
            ]
        }
    )


def test_canonical_claim_rejects_unsupported_not_satisfied_inference(diabetes_policy):
    """An LLM cannot label existing passing evidence as NOT_SATISFIED."""
    provider = MockLLMProvider(
        response_generator=lambda prompt, _system: _single_criterion_response(
            prompt, "NOT_SATISFIED"
        )
    )
    agent = DecisionAgent(llm_provider=provider)

    result = agent.evaluate_canonical_claim(_canonical_claim(), diabetes_policy.model_dump(mode="json"))

    assert result.outcome == DecisionOutcome.HUMAN_REVIEW
    assert "NOT_SATISFIED assessment is unsupported" in result.errors[0]
    assert provider.call_count == 1


def test_canonical_assessment_rejects_nonexistent_evidence_path(diabetes_policy):
    provider = MockLLMProvider(
        response_generator=lambda prompt, _system: _single_criterion_response(
            prompt, path_override="$.evidence[9].extracted_facts.hba1c"
        )
    )

    result = DecisionAgent(llm_provider=provider).evaluate_canonical_claim(
        _canonical_claim(), diabetes_policy.model_dump(mode="json")
    )

    assert result.outcome == DecisionOutcome.HUMAN_REVIEW
    assert "missing canonical path" in result.errors[0]


def test_canonical_assessment_rejects_invented_output_fields(diabetes_policy):
    def invented_field(prompt, _system):
        payload = json.loads(_single_criterion_response(prompt))
        payload["criterion_assessments"][0]["invented_fact"] = {"hba1c": 99.0}
        return json.dumps(payload)
    provider = MockLLMProvider(response_generator=invented_field)

    result = DecisionAgent(llm_provider=provider).evaluate_canonical_claim(
        _canonical_claim(), diabetes_policy.model_dump(mode="json")
    )

    assert result.outcome == DecisionOutcome.HUMAN_REVIEW
    assert "Criterion assessment layer failed" in result.errors[0]


def test_canonical_assessment_requires_every_rag_criterion(diabetes_policy):
    provider = MockLLMProvider(response_generator=lambda _p, _s: json.dumps({"criterion_assessments": []}))

    result = DecisionAgent(llm_provider=provider).evaluate_canonical_claim(
        _canonical_claim(), diabetes_policy.model_dump(mode="json")
    )

    assert result.outcome == DecisionOutcome.HUMAN_REVIEW
    assert "cover each RAG policy criterion exactly once" in result.errors[0]


def test_canonical_claim_prompt_contains_only_new_contract_payload(diabetes_policy):
    prompt = build_criterion_assessment_prompt(
        CanonicalClaim.model_validate(_canonical_claim()), diabetes_policy.criteria[0]
    )
    assert "canonical_claim" in prompt
    assert "rag_criterion" in prompt
    assert "criterion_interpretations" not in prompt
    assert "Do not make a final claim decision" in CRITERION_ASSESSMENT_SYSTEM_PROMPT


def test_phase2_all_criteria_satisfied_approves_deterministically(diabetes_policy):
    provider = MockLLMProvider(response_generator=lambda prompt, _s: _single_criterion_response(prompt))
    result = DecisionAgent(llm_provider=provider).evaluate_canonical_claim(
        _canonical_claim(), diabetes_policy.model_dump(mode="json")
    )
    assert result.outcome == DecisionOutcome.APPROVE
    assert provider.call_count == 2


def test_phase2_not_satisfied_rejects_only_with_canonical_support(diabetes_policy):
    claim = _canonical_claim()
    claim["case_data"]["clinical_metrics"]["HbA1c"] = 7.5
    claim["evidence"][0]["extracted_facts"]["hba1c"] = 7.5
    provider = MockLLMProvider(
        response_generator=lambda prompt, _s: _single_criterion_response(prompt, "NOT_SATISFIED")
    )
    result = DecisionAgent(llm_provider=provider).evaluate_canonical_claim(
        claim, diabetes_policy.model_dump(mode="json")
    )
    assert result.outcome == DecisionOutcome.REJECT


def test_phase2_supported_but_below_threshold_still_rejects_deterministically(diabetes_policy):
    """The LLM may only confirm evidence readability; the deterministic rule still decides the final outcome."""
    claim = _canonical_claim()
    claim["case_data"]["clinical_metrics"]["HbA1c"] = 7.2
    claim["evidence"][0]["extracted_facts"]["hba1c"] = 7.2

    def supported_but_failing(prompt, _system):
        return json.dumps({
            "status": "SUPPORTED",
            "selected_paths": [1],
            "reason": "HbA1c value is present and readable.",
        })

    provider = MockLLMProvider(response_generator=supported_but_failing)
    result = DecisionAgent(llm_provider=provider).evaluate_canonical_claim(
        claim, diabetes_policy.model_dump(mode="json")
    )

    assert result.outcome == DecisionOutcome.REJECT
    assert result.criterion_assessments["CRT-HBA1C"].status == CriterionAssessmentStatus.NOT_SATISFIED


def test_phase2_missing_mandatory_evidence_requests_more_information(diabetes_policy):
    claim = _canonical_claim()
    claim["evidence"] = [claim["evidence"][1]]

    def missing_hba1c(prompt, _s):
        criterion_id = json.loads(prompt)["rag_criterion"]["criterion_id"]
        if criterion_id == "CRT-HBA1C":
            return json.dumps({"criterion_assessments": [{
                "criterion_id": criterion_id,
                "status": "MISSING",
                "evidence_paths": [],
                "required_evidence_paths": ["hba1c_report"],
                "reasoning": "No canonical HbA1c evidence exists.",
            }]})
        return json.dumps({"criterion_assessments": [{
            "criterion_id": criterion_id,
            "status": "SATISFIED",
            "evidence_paths": ["$.evidence[0].extracted_facts.systolic_bp"],
            "reasoning": "Canonical blood-pressure evidence exists.",
        }]})

    result = DecisionAgent(llm_provider=MockLLMProvider(response_generator=missing_hba1c)).evaluate_canonical_claim(
        claim, diabetes_policy.model_dump(mode="json")
    )
    assert result.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION


@pytest.mark.parametrize("status", ["UNCERTAIN", "CONFLICTING"])
def test_phase2_safety_statuses_lead_to_human_review(diabetes_policy, status):
    provider = MockLLMProvider(
        response_generator=lambda prompt, _s: _single_criterion_response(prompt, status)
    )
    result = DecisionAgent(llm_provider=provider).evaluate_canonical_claim(
        _canonical_claim(), diabetes_policy.model_dump(mode="json")
    )
    assert result.outcome == DecisionOutcome.HUMAN_REVIEW


def test_phase2_not_applicable_does_not_grant_mandatory_satisfaction(diabetes_policy):
    diabetes_policy.criteria[0].applicability_rule = Rule(
        field="diagnoses", operator="contains", value="Z99"
    )
    provider = MockLLMProvider(
        response_generator=lambda prompt, _s: _single_criterion_response(prompt, "NOT_APPLICABLE")
    )
    result = DecisionAgent(llm_provider=provider).evaluate_canonical_claim(
        _canonical_claim(), diabetes_policy.model_dump(mode="json")
    )
    # The canonical claim, not NOT_APPLICABLE, supports the approval.
    assert result.outcome == DecisionOutcome.APPROVE


def test_phase2_resubmission_uses_changed_canonical_data(diabetes_policy):
    def dynamic_response(prompt, _s):
        payload = json.loads(prompt)
        claim = payload["canonical_claim"]
        hba1c_val = claim["case_data"]["clinical_metrics"].get("HbA1c", 8.5)
        status = "SATISFIED" if hba1c_val > 8.0 else "NOT_SATISFIED"
        return _single_criterion_response(prompt, hba1c_status=status)

    provider = MockLLMProvider(response_generator=dynamic_response)
    agent = DecisionAgent(llm_provider=provider)
    first = agent.evaluate_canonical_claim(_canonical_claim("RESUBMIT-1"), diabetes_policy.model_dump(mode="json"))
    resubmitted = _canonical_claim("RESUBMIT-1")
    resubmitted["case_data"]["clinical_metrics"]["HbA1c"] = 7.5
    resubmitted["evidence"][0]["extracted_facts"]["hba1c"] = 7.5
    second = agent.evaluate_canonical_claim(resubmitted, diabetes_policy.model_dump(mode="json"))

    assert first.outcome == DecisionOutcome.APPROVE
    assert second.outcome == DecisionOutcome.REJECT
    assert provider.call_count == 4


def test_phase2_prompt_includes_only_requested_rag_criterion_metadata(diabetes_policy):
    criterion = diabetes_policy.criteria[0]
    criterion.interpretation_guidance = "Use only final laboratory results."
    criterion.required_evidence = ["hba1c_report"]
    criterion.evaluation_type = "threshold"
    prompt = build_criterion_assessment_prompt(
        CanonicalClaim.model_validate(_canonical_claim()),
        criterion,
    )
    payload = json.loads(prompt)
    assert payload["rag_criterion"]["interpretation_guidance"] == "Use only final laboratory results."
    assert payload["rag_criterion"]["required_evidence"] == ["hba1c_report"]
    assert payload["rag_criterion"]["evaluation_type"] == "threshold"
    assert "CRT-BP" not in prompt


def test_external_input_format_evaluation():
    external_claim = {
        "claim_id": "CLM-NEW-001",
        "patient": {
            "patient_id": "PAT-NEW-001",
            "age": 66,
            "gender": "Male"
        },
        "insurance": {
            "primary": {},
            "secondary": None
        },
        "diagnoses": ["E11.9"],
        "procedure": {
            "code": "PROC-99"
        },
        "clinical_information": {
            "hba1c_report": {
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {"hba1c": 8.5}
            }
        },
        "treatment_history": {},
        "diagnostic_information": {},
        "documents": [],
        "submission": {
            "attempt": 1,
            "date": "2026-08-12"
        }
    }

    external_policy = {
        "claim_id": "CLM-NEW-001",
        "matched_policies": [
            {
                "policy_id": "POL-NEW-001",
                "relevance": 0.98
            }
        ],
        "criteria": [
            {
                "criterion_id": "CRT-HBA1C",
                "requirement": "HbA1c above 8.0%",
                "source": "POL-NEW-001",
                "mandatory": True,
                "required_evidence_keys": ["hba1c_report"],
                "clinical_rule": {
                    "field": "clinical_metrics.hba1c",
                    "operator": "gt",
                    "value": 8.0
                },
                "evidence_rule": {
                    "field": "hba1c",
                    "operator": "gt",
                    "value": 8.0
                }
            }
        ]
    }

    def _external_single_criterion_response(prompt, hba1c_status="SATISFIED"):
        criterion_id = json.loads(prompt)["rag_criterion"]["criterion_id"]
        return json.dumps(
            {
                "criterion_assessments": [
                    {
                        "criterion_id": criterion_id,
                        "status": hba1c_status,
                        "evidence_paths": ["$.clinical_information.hba1c_report.extracted_facts.hba1c"],
                        "reasoning": ["HbA1c level is satisfied in clinical metrics.", "Verified via lab report."],
                    }
                ]
            }
        )

    provider = MockLLMProvider(response_generator=lambda prompt, _s: _external_single_criterion_response(prompt))
    agent = DecisionAgent(llm_provider=provider)
    result = agent.evaluate_canonical_claim(external_claim, external_policy)

    assert result.outcome == DecisionOutcome.APPROVE
    assert result.case_id == "CLM-NEW-001"
    assert result.criteria_results["CRT-HBA1C"] is True

    # Verify exact externally consumable fields:
    assessment = result.criterion_assessments["CRT-HBA1C"]
    assert assessment.evidence_paths == ["$.clinical_information.hba1c_report.extracted_facts.hba1c"]
    assert "$.evidence" not in assessment.evidence_paths[0]
    assert isinstance(assessment.reasoning, list)
    assert assessment.reasoning == ["HbA1c level is satisfied in clinical metrics.", "Verified via lab report."]


def test_external_input_resubmission_changed_data():
    external_claim = {
        "claim_id": "CLM-NEW-002",
        "patient": {
            "patient_id": "PAT-NEW-002",
            "age": 45,
            "gender": "Female"
        },
        "insurance": {"primary": {}, "secondary": None},
        "diagnoses": ["E11.9"],
        "procedure": None,
        "clinical_information": {
            "hba1c_report": {
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {"hba1c": 8.5}
            }
        },
        "treatment_history": {},
        "diagnostic_information": {},
        "documents": [],
        "submission": {"attempt": 1, "date": "2026-08-12"}
    }

    external_policy = {
        "claim_id": "CLM-NEW-002",
        "matched_policies": [{"policy_id": "POL-NEW-002", "relevance": 0.95}],
        "criteria": [
            {
                "criterion_id": "CRT-HBA1C",
                "requirement": "HbA1c above 8.0%",
                "source": "POL-NEW-002",
                "mandatory": True,
                "required_evidence_keys": ["hba1c_report"],
                "clinical_rule": {
                    "field": "clinical_metrics.hba1c",
                    "operator": "gt",
                    "value": 8.0
                },
                "evidence_rule": {
                    "field": "hba1c",
                    "operator": "gt",
                    "value": 8.0
                }
            }
        ]
    }

    def dynamic_response(prompt, _s):
        payload = json.loads(prompt)
        claim = payload["canonical_claim"]
        hba1c_val = claim["clinical_information"]["hba1c_report"]["extracted_facts"].get("hba1c", 8.5)
        status = "SATISFIED" if hba1c_val > 8.0 else "NOT_SATISFIED"
        return json.dumps(
            {
                "criterion_assessments": [
                    {
                        "criterion_id": "CRT-HBA1C",
                        "status": status,
                        "evidence_paths": ["$.clinical_information.hba1c_report.extracted_facts.hba1c"],
                        "reasoning": [f"HbA1c level {hba1c_val} checked against threshold."],
                    }
                ]
            }
        )

    provider = MockLLMProvider(response_generator=dynamic_response)
    agent = DecisionAgent(llm_provider=provider)
    
    first = agent.evaluate_canonical_claim(external_claim, external_policy)
    assert first.outcome == DecisionOutcome.APPROVE
    assert first.criterion_assessments["CRT-HBA1C"].evidence_paths == ["$.clinical_information.hba1c_report.extracted_facts.hba1c"]

    resubmitted_claim = dict(external_claim)
    resubmitted_claim["clinical_information"] = {
        "hba1c_report": {
            "status": "verified",
            "confidence_score": 0.95,
            "extracted_facts": {"hba1c": 7.2}
        }
    }
    
    second = agent.evaluate_canonical_claim(resubmitted_claim, external_policy)
    assert second.outcome == DecisionOutcome.REJECT
    assert second.criterion_assessments["CRT-HBA1C"].evidence_paths == ["$.clinical_information.hba1c_report.extracted_facts.hba1c"]


def test_optimized_llm_interaction_suite():
    # Setup claim with both relevant and irrelevant data
    claim = {
        "claim_id": "CLM-OPT-001",
        "patient": {"patient_id": "PAT-OPT-001", "age": 50, "gender": "Male"},
        "diagnoses": ["E11.9"],
        "procedure": {"code": "PROC-99"},
        "clinical_information": {
            "hba1c_report": {
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {"hba1c": 8.5}
            },
            "unrelated_report": {
                "status": "verified",
                "extracted_facts": {"bp": 120}
            }
        },
        "treatment_history": {
            "past_treatment": "metformin"
        },
        "submission": {"attempt": 1, "date": "2026-08-12"}
    }

    policy = {
        "matched_policies": [{"policy_id": "POL-OPT-001", "relevance": 1.0}],
        "criteria": [
            {
                "criterion_id": "CRT-HBA1C",
                "requirement": "HbA1c above 8.0%",
                "source": "POL-OPT-001",
                "mandatory": True,
                "required_evidence_keys": ["hba1c_report"],
                "clinical_rule": {
                    "field": "clinical_metrics.hba1c",
                    "operator": "gt",
                    "value": 8.0
                },
                "evidence_rule": {
                    "field": "hba1c",
                    "operator": "gt",
                    "value": 8.0
                }
            }
        ]
    }

    # 1. Verify relevant canonical data is sent, and unrelated data is excluded
    def check_minimized_payload(prompt, _s):
        payload = json.loads(prompt)
        claim_data = payload["relevant_claim_data"]
        assert "hba1c_report" in claim_data["clinical_information"]
        assert "unrelated_report" not in claim_data["clinical_information"]
        assert "treatment_history" not in claim_data
        
        hba1c_idx = None
        for item in payload["candidate_paths"]:
            if item.endswith("extracted_facts.hba1c"):
                hba1c_idx = int(item.split(":")[0])
                break
        assert hba1c_idx is not None
        
        return json.dumps({
            "status": "SUPPORTED",
            "selected_paths": [hba1c_idx],
            "reason": "HbA1c level is 8.5% which is above 8.0%."
        })

    provider = MockLLMProvider(response_generator=check_minimized_payload)
    agent = DecisionAgent(llm_provider=provider)
    res = agent.evaluate_canonical_claim(claim, policy)
    assert res.outcome == DecisionOutcome.APPROVE
    assert res.criterion_assessments["CRT-HBA1C"].status == "SATISFIED"
    assert res.criterion_assessments["CRT-HBA1C"].evidence_paths == ["$.clinical_information.hba1c_report.extracted_facts.hba1c"]
    assert res.criterion_assessments["CRT-HBA1C"].reasoning == ["HbA1c level is 8.5% which is above 8.0%."]

    # 2. Verify only allowed statuses are accepted (disallowed status fails closed)
    def check_disallowed_status(prompt, _s):
        return json.dumps({
            "status": "SATISFIED",
            "selected_paths": [1],
            "reason": "satisfied status is invalid here"
        })
    provider2 = MockLLMProvider(response_generator=check_disallowed_status)
    agent2 = DecisionAgent(llm_provider=provider2)
    res2 = agent2.evaluate_canonical_claim(claim, policy)
    assert res2.outcome == DecisionOutcome.HUMAN_REVIEW
    assert "Invalid status classified by LLM" in res2.errors[0]

    # 3. Verify invalid path selection fails closed
    def check_invalid_path(prompt, _s):
        return json.dumps({
            "status": "SUPPORTED",
            "selected_paths": [999],
            "reason": "invalid index"
        })
    provider3 = MockLLMProvider(response_generator=check_invalid_path)
    agent3 = DecisionAgent(llm_provider=provider3)
    res3 = agent3.evaluate_canonical_claim(claim, policy)
    assert res3.outcome == DecisionOutcome.HUMAN_REVIEW
    assert "Invalid path index selection" in res3.errors[0]

    # 4. Verify malformed LLM JSON output fails closed
    def check_malformed_json(prompt, _s):
        return "this is not JSON"
    provider4 = MockLLMProvider(response_generator=check_malformed_json)
    agent4 = DecisionAgent(llm_provider=provider4)
    res4 = agent4.evaluate_canonical_claim(claim, policy)
    assert res4.outcome == DecisionOutcome.HUMAN_REVIEW

    # 5. Verify outcome REJECT works
    def check_reject_payload(prompt, _s):
        return json.dumps({
            "status": "SUPPORTED",
            "selected_paths": [1],
            "reason": "HbA1c is below threshold"
        })
    rejecting_claim = dict(claim)
    rejecting_claim["clinical_information"] = {
        "hba1c_report": {
            "status": "verified",
            "confidence_score": 0.95,
            "extracted_facts": {"hba1c": 7.2}
        }
    }
    provider5 = MockLLMProvider(response_generator=check_reject_payload)
    agent5 = DecisionAgent(llm_provider=provider5)
    res5 = agent5.evaluate_canonical_claim(rejecting_claim, policy)
    assert res5.outcome == DecisionOutcome.REJECT
    assert res5.criterion_assessments["CRT-HBA1C"].status == "NOT_SATISFIED"

    # 6. Verify outcome REQUEST_MORE_INFORMATION works
    def check_missing_payload(prompt, _s):
        return json.dumps({
            "status": "MISSING",
            "selected_paths": [],
            "reason": "hba1c_report is missing from claim"
        })
    missing_claim = dict(claim)
    missing_claim["clinical_information"] = {}
    provider6 = MockLLMProvider(response_generator=check_missing_payload)
    agent6 = DecisionAgent(llm_provider=provider6)
    res6 = agent6.evaluate_canonical_claim(missing_claim, policy)
    assert res6.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
    assert res6.criterion_assessments["CRT-HBA1C"].status == "MISSING"

    # 7. Verify outcome HUMAN_REVIEW works (via CONFLICTING status)
    def check_conflicting_payload(prompt, _s):
        return json.dumps({
            "status": "CONFLICTING",
            "selected_paths": [1],
            "reason": "conflicting reports"
        })
    provider7 = MockLLMProvider(response_generator=check_conflicting_payload)
    agent7 = DecisionAgent(llm_provider=provider7)
    res7 = agent7.evaluate_canonical_claim(claim, policy)
    assert res7.outcome == DecisionOutcome.HUMAN_REVIEW
    assert res7.criterion_assessments["CRT-HBA1C"].status == "CONFLICTING"

    # 8. Verify outcome HUMAN_REVIEW works (via UNCERTAIN status)
    def check_uncertain_payload(prompt, _s):
        return json.dumps({
            "status": "UNCERTAIN",
            "selected_paths": [1],
            "reason": "report value is blurred"
        })
    provider8 = MockLLMProvider(response_generator=check_uncertain_payload)
    agent8 = DecisionAgent(llm_provider=provider8)
    res8 = agent8.evaluate_canonical_claim(claim, policy)
    assert res8.outcome == DecisionOutcome.HUMAN_REVIEW
    assert res8.criterion_assessments["CRT-HBA1C"].status == "UNCERTAIN"

    # 9. Verify Resubmission flow (8.5 -> APPROVE, then 7.4 -> REJECT) using fresh canonical data
    def dynamic_evidence_interpretation(prompt, _s):
        return json.dumps({
            "status": "SUPPORTED",
            "selected_paths": [1],
            "reason": "HbA1c value exists in clinical information report."
        })
    provider9 = MockLLMProvider(response_generator=dynamic_evidence_interpretation)
    agent9 = DecisionAgent(llm_provider=provider9)
    
    # First submission: HbA1c = 8.5 (PASS) -> Outcome: APPROVE
    res_first = agent9.evaluate_canonical_claim(claim, policy)
    assert res_first.outcome == DecisionOutcome.APPROVE
    
    # Second submission: HbA1c = 7.4 (FAIL) -> Outcome: REJECT
    resubmitted = dict(claim)
    resubmitted["clinical_information"] = {
        "hba1c_report": {
            "status": "verified",
            "confidence_score": 0.95,
            "extracted_facts": {"hba1c": 7.4}
        }
    }
    res_second = agent9.evaluate_canonical_claim(resubmitted, policy)
    assert res_second.outcome == DecisionOutcome.REJECT


