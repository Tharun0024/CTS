import json
import pytest
from decision_agent.agent import DecisionAgent
from decision_agent.schemas import DecisionOutcome, CriterionAssessmentStatus
from decision_agent.llm_provider import MockLLMProvider

# Shared integration test RAG policy
INTEGRATION_POLICY = {
    "claim_id": "CLM-001",
    "matched_policies": [
        {
            "policy_id": "AETNA-CPB-0660"
        }
    ],
    "criteria": [
        {
            "criterion_id": "CRT-HBA1C",
            "requirement": "HbA1c above 8.0%",
            "source": "AETNA-CPB-0660",
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


def test_integration_case_1_initial():
    """
    Case 1: INITIAL evaluation.
    PAT-001 / CLM-001 / attempt 1
    HbA1c = 8.5, policy > 8.0
    Expected: LLM SUPPORTED -> deterministic evaluation -> APPROVE.
    """
    claim = {
        "claim_id": "CLM-001",
        "patient": {
            "patient_id": "PAT-001",
            "age": 66,
            "gender": "Male"
        },
        "clinical_information": {
            "hba1c_report": {
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {
                    "hba1c": 8.5
                }
            }
        },
        "submission": {
            "attempt": 1,
            "date": "2026-08-12"
        }
    }

    def check_initial_prompt(prompt, _s):
        payload = json.loads(prompt)
        assert payload["evidence_key"] == "hba1c_report"
        hba1c_idx = None
        for item in payload["candidate_paths"]:
            if item.endswith("extracted_facts.hba1c"):
                hba1c_idx = int(item.split(":")[0])
                break
        assert hba1c_idx is not None

        return json.dumps({
            "status": "SUPPORTED",
            "selected_paths": [hba1c_idx],
            "reason": ["HbA1c value 8.5 is present and clearly readable."]
        })

    provider = MockLLMProvider(response_generator=check_initial_prompt)
    agent = DecisionAgent(llm_provider=provider)
    res = agent.evaluate_canonical_claim(claim, INTEGRATION_POLICY)

    assert res.outcome == DecisionOutcome.APPROVE
    assert res.claim_id == "CLM-001"
    assert res.policy_id == "AETNA-CPB-0660"
    assert res.submission_attempt == 1
    assert res.criterion_assessments["CRT-HBA1C"].status == CriterionAssessmentStatus.SATISFIED
    assert res.criterion_assessments["CRT-HBA1C"].evidence_paths == [
        "$.clinical_information.hba1c_report.extracted_facts.hba1c"
    ]
    assert res.criterion_assessments["CRT-HBA1C"].reasoning == [
        "HbA1c value 8.5 is present and clearly readable."
    ]
    assert res.criteria_results["CRT-HBA1C"] is True


def test_integration_case_2_resubmission():
    """
    Case 2: RESUBMISSION.
    Same patient/claim, attempt 2
    HbA1c = 7.4
    Expected: LLM SUPPORTED -> deterministic evaluation -> REJECT.
    Verify attempt 2 does not reuse attempt 1 data/LLM results, and attempt history is distinguishable.
    """
    claim_1 = {
        "claim_id": "CLM-001",
        "patient": {
            "patient_id": "PAT-001",
            "age": 66,
            "gender": "Male"
        },
        "clinical_information": {
            "hba1c_report": {
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {
                    "hba1c": 8.5
                }
            }
        },
        "submission": {
            "attempt": 1,
            "date": "2026-08-12"
        }
    }

    claim_2 = {
        "claim_id": "CLM-001",
        "patient": {
            "patient_id": "PAT-001",
            "age": 66,
            "gender": "Male"
        },
        "clinical_information": {
            "hba1c_report": {
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {
                    "hba1c": 7.4
                }
            }
        },
        "submission": {
            "attempt": 2,
            "date": "2026-08-13"
        }
    }

    def check_resubmission_prompt(prompt, _s):
        payload = json.loads(prompt)
        claim_data = payload["relevant_claim_data"]
        hba1c_val = claim_data["clinical_information"]["hba1c_report"]["extracted_facts"]["hba1c"]
        
        # Get path index of hba1c
        hba1c_idx = None
        for item in payload["candidate_paths"]:
            if item.endswith("extracted_facts.hba1c"):
                hba1c_idx = int(item.split(":")[0])
                break
        assert hba1c_idx is not None

        return json.dumps({
            "status": "SUPPORTED",
            "selected_paths": [hba1c_idx],
            "reason": [f"HbA1c value {hba1c_val} is present and clearly readable."]
        })

    provider = MockLLMProvider(response_generator=check_resubmission_prompt)
    agent = DecisionAgent(llm_provider=provider)

    # Attempt 1
    res1 = agent.evaluate_canonical_claim(claim_1, INTEGRATION_POLICY)
    assert res1.outcome == DecisionOutcome.APPROVE
    assert res1.submission_attempt == 1
    assert res1.criterion_assessments["CRT-HBA1C"].status == CriterionAssessmentStatus.SATISFIED

    # Attempt 2
    res2 = agent.evaluate_canonical_claim(claim_2, INTEGRATION_POLICY)
    assert res2.outcome == DecisionOutcome.REJECT
    assert res2.submission_attempt == 2
    assert res2.criterion_assessments["CRT-HBA1C"].status == CriterionAssessmentStatus.NOT_SATISFIED

    # Verify distinguishable and no shared state
    assert res1 is not res2
    assert res1.submission_attempt == 1
    assert res2.submission_attempt == 2
    assert res1.outcome == DecisionOutcome.APPROVE
    assert res2.outcome == DecisionOutcome.REJECT


def test_integration_case_3_missing():
    """
    Case 3: MISSING evidence.
    No HbA1c evidence
    Expected: MISSING -> REQUEST_MORE_INFORMATION.
    """
    claim = {
        "claim_id": "CLM-001",
        "patient": {
            "patient_id": "PAT-001",
            "age": 66,
            "gender": "Male"
        },
        "clinical_information": {},
        "submission": {
            "attempt": 1,
            "date": "2026-08-12"
        }
    }

    def check_missing_prompt(prompt, _s):
        return json.dumps({
            "status": "MISSING",
            "selected_paths": [],
            "reason": ["HbA1c report is missing from the submitted clinical evidence."]
        })

    provider = MockLLMProvider(response_generator=check_missing_prompt)
    agent = DecisionAgent(llm_provider=provider)
    res = agent.evaluate_canonical_claim(claim, INTEGRATION_POLICY)

    assert res.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
    assert res.claim_id == "CLM-001"
    assert res.submission_attempt == 1
    assert res.criterion_assessments["CRT-HBA1C"].status == CriterionAssessmentStatus.MISSING
    assert res.criterion_assessments["CRT-HBA1C"].evidence_paths == []
    assert res.criterion_assessments["CRT-HBA1C"].required_evidence_paths == ["hba1c_report"]


def test_integration_case_4_conflict():
    """
    Case 4: CONFLICT.
    Conflicting HbA1c evidence
    Expected: CONFLICTING -> HUMAN_REVIEW.
    """
    claim = {
        "claim_id": "CLM-001",
        "patient": {
            "patient_id": "PAT-001",
            "age": 66,
            "gender": "Male"
        },
        "clinical_information": {
            "hba1c_report": {
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {
                    "hba1c": 8.5
                }
            }
        },
        "submission": {
            "attempt": 1,
            "date": "2026-08-12"
        }
    }

    def check_conflict_prompt(prompt, _s):
        return json.dumps({
            "status": "CONFLICTING",
            "selected_paths": [1],
            "reason": ["Conflicting laboratory report values found."]
        })

    provider = MockLLMProvider(response_generator=check_conflict_prompt)
    agent = DecisionAgent(llm_provider=provider)
    res = agent.evaluate_canonical_claim(claim, INTEGRATION_POLICY)

    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert res.claim_id == "CLM-001"
    assert res.submission_attempt == 1
    assert res.criterion_assessments["CRT-HBA1C"].status == CriterionAssessmentStatus.CONFLICTING


def test_integration_case_5_safety_failures():
    """
    Case 5: SAFETY.
    Malformed LLM output, invalid path, missing criterion assessment, or provider failure
    Expected: fail closed to HUMAN_REVIEW.
    """
    claim = {
        "claim_id": "CLM-001",
        "patient": {
            "patient_id": "PAT-001",
            "age": 66,
            "gender": "Male"
        },
        "clinical_information": {
            "hba1c_report": {
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {
                    "hba1c": 8.5
                }
            }
        },
        "submission": {
            "attempt": 1,
            "date": "2026-08-12"
        }
    }

    # 1. Malformed LLM output
    provider_malformed = MockLLMProvider(response_generator=lambda p, s: "invalid raw json string")
    agent_malformed = DecisionAgent(llm_provider=provider_malformed)
    res_malformed = agent_malformed.evaluate_canonical_claim(claim, INTEGRATION_POLICY)
    assert res_malformed.outcome == DecisionOutcome.HUMAN_REVIEW
    assert len(res_malformed.errors) > 0

    # 2. Invalid path index selection
    provider_invalid_path = MockLLMProvider(response_generator=lambda p, s: json.dumps({
        "status": "SUPPORTED",
        "selected_paths": [9999],
        "reason": ["invalid index selected"]
    }))
    agent_invalid_path = DecisionAgent(llm_provider=provider_invalid_path)
    res_invalid_path = agent_invalid_path.evaluate_canonical_claim(claim, INTEGRATION_POLICY)
    assert res_invalid_path.outcome == DecisionOutcome.HUMAN_REVIEW
    assert len(res_invalid_path.errors) > 0

    # 3. Provider failure (throws exception)
    def raise_err(p, s):
        raise RuntimeError("LLM Provider Unavailable")

    provider_fail = MockLLMProvider(response_generator=raise_err)
    agent_fail = DecisionAgent(llm_provider=provider_fail)
    res_fail = agent_fail.evaluate_canonical_claim(claim, INTEGRATION_POLICY)
    assert res_fail.outcome == DecisionOutcome.HUMAN_REVIEW
    assert len(res_fail.errors) > 0


def test_independence_verifications():
    """
    Ensure DecisionAgent does not import any database connection modules,
    raw Synthea files, or raw documents parser modules.
    """
    import sys
    assert "sqlite3" not in sys.modules
    assert "psycopg2" not in sys.modules
    # Ensure no db module from our project is loaded unless mock/utils
    forbidden_imports = ["synthea", "database", "db_client", "raw_documents"]
    for mod in sys.modules:
        assert not any(forbidden in mod for forbidden in forbidden_imports), f"Forbidden import found: {mod}"
