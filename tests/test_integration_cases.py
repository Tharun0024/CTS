import json
import pytest
from transformation.canonical_claim import build_canonical_claim
from adapters.rag_adapter import build_rag_policy
from decision.agent import DecisionAgent
from decision.schemas import DecisionOutcome, CriterionAssessmentStatus
from decision.llm_provider import MockLLMProvider

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


def test_runtime_transformation_initial_submission_direct_to_agent():
    """Version-1 runtime output should pass directly through the canonical contract without legacy mapping."""
    runtime_claim = {
        "claim_id": "CLR-TRANS-001",
        "patient": {"patient_id": "PAT-TRANS-001", "age": 52, "gender": "Female"},
        "diagnoses": ["E11.9"],
        "clinical_information": {
            "hba1c_report": {"status": "verified", "confidence_score": 0.95, "extracted_facts": {"hba1c": 8.7}},
            "bp_report": {"status": "verified", "confidence_score": 0.92, "extracted_facts": {"systolic_bp": 128}},
        },
        "submission": {"attempt": 1, "date": "2026-08-14"},
    }
    runtime_policy = {
        "claim_id": "CLR-TRANS-001",
        "matched_policies": [{"policy_id": "POL-TRANS-001", "name": "Runtime Contract Policy"}],
        "criteria": [
            {
                "criterion_id": "CRT-HBA1C",
                "requirement": "HbA1c above 8.0%",
                "mandatory": True,
                "required_evidence_keys": ["hba1c_report"],
                "clinical_rule": {"field": "clinical_metrics.hba1c", "operator": "gt", "value": 8.0},
                "evidence_rule": {"field": "hba1c", "operator": "gt", "value": 8.0},
            },
            {
                "criterion_id": "CRT-BP",
                "requirement": "Systolic BP <= 140",
                "mandatory": True,
                "required_evidence_keys": ["bp_report"],
                "clinical_rule": {"field": "clinical_metrics.systolic_bp", "operator": "lte", "value": 140},
                "evidence_rule": {"field": "systolic_bp", "operator": "lte", "value": 140},
            },
        ],
    }

    canonical_claim = build_canonical_claim(runtime_claim)
    rag_policy = build_rag_policy(runtime_policy)
    assert canonical_claim["case_data"]["clinical_metrics"]["hba1c"] == 8.7
    assert canonical_claim["evidence"][0]["evidence_key"] == "hba1c_report"
    assert rag_policy["criteria"][0]["criterion_id"] == "CRT-HBA1C"

    def response_for(prompt, _system):
        payload = json.loads(prompt)
        status = "SUPPORTED"
        selected = []
        if payload["evidence_key"] == "hba1c_report":
            for entry in payload["candidate_paths"]:
                if entry.endswith("extracted_facts.hba1c"):
                    selected = [int(entry.split(":", 1)[0])]
                    break
        elif payload["evidence_key"] == "bp_report":
            for entry in payload["candidate_paths"]:
                if entry.endswith("extracted_facts.systolic_bp"):
                    selected = [int(entry.split(":", 1)[0])]
                    break
        return json.dumps({"status": status, "selected_paths": selected, "reason": ["Evidence is present and readable."]})

    provider = MockLLMProvider(response_generator=response_for)
    agent = DecisionAgent(llm_provider=provider)
    res = agent.evaluate_canonical_claim(canonical_claim, rag_policy)

    assert res.outcome == DecisionOutcome.APPROVE
    assert res.policy_id == "POL-TRANS-001"
    assert res.submission_attempt == 1
    assert set(res.criteria_results) == {"CRT-HBA1C", "CRT-BP"}
    assert all(res.criteria_results.values())


def test_runtime_transformation_resubmission_evaluates_current_claim_only():
    """Resubmissions must evaluate the current canonical claim, not cached prior LLM state."""
    runtime_claim_1 = {
        "claim_id": "CLR-TRANS-002",
        "patient": {"patient_id": "PAT-TRANS-002", "age": 61, "gender": "Male"},
        "clinical_information": {"hba1c_report": {"status": "verified", "confidence_score": 0.95, "extracted_facts": {"hba1c": 8.8}}},
        "submission": {"attempt": 1, "date": "2026-08-14"},
    }
    runtime_claim_2 = {
        "claim_id": "CLR-TRANS-002",
        "patient": {"patient_id": "PAT-TRANS-002", "age": 61, "gender": "Male"},
        "clinical_information": {"hba1c_report": {"status": "verified", "confidence_score": 0.95, "extracted_facts": {"hba1c": 7.2}}},
        "submission": {"attempt": 2, "date": "2026-08-15"},
    }
    runtime_policy = {
        "claim_id": "CLR-TRANS-002",
        "matched_policies": [{"policy_id": "POL-TRANS-002", "name": "Runtime Contract Policy"}],
        "criteria": [
            {"criterion_id": "CRT-HBA1C", "requirement": "HbA1c above 8.0%", "mandatory": True, "required_evidence_keys": ["hba1c_report"], "clinical_rule": {"field": "clinical_metrics.hba1c", "operator": "gt", "value": 8.0}, "evidence_rule": {"field": "hba1c", "operator": "gt", "value": 8.0}},
        ],
    }

    canonical_1 = build_canonical_claim(runtime_claim_1)
    canonical_2 = build_canonical_claim(runtime_claim_2)
    rag_policy = build_rag_policy(runtime_policy)

    def response_for(prompt, _system):
        payload = json.loads(prompt)
        claim = payload["relevant_claim_data"]
        val = claim["case_data"]["clinical_metrics"]["hba1c"]
        selected = []
        for entry in payload["candidate_paths"]:
            if entry.endswith("extracted_facts.hba1c"):
                selected = [int(entry.split(":", 1)[0])]
                break
        return json.dumps({"status": "SUPPORTED", "selected_paths": selected, "reason": [f"HbA1c value {val} is present and readable."]})

    provider = MockLLMProvider(response_generator=response_for)
    agent = DecisionAgent(llm_provider=provider)

    first = agent.evaluate_canonical_claim(canonical_1, rag_policy)
    second = agent.evaluate_canonical_claim(canonical_2, rag_policy)

    assert first.outcome == DecisionOutcome.APPROVE
    assert second.outcome == DecisionOutcome.REJECT
    assert first.submission_attempt == 1
    assert second.submission_attempt == 2


def test_runtime_transformation_missing_evidence_requests_more_information():
    """Missing evidence must still map to the canonical claim and produce MISSING semantics."""
    runtime_claim = {
        "claim_id": "CLR-TRANS-003",
        "patient": {"patient_id": "PAT-TRANS-003", "age": 63, "gender": "Female"},
        "clinical_information": {},
        "submission": {"attempt": 1, "date": "2026-08-14"},
    }
    runtime_policy = {
        "claim_id": "CLR-TRANS-003",
        "matched_policies": [{"policy_id": "POL-TRANS-003", "name": "Runtime Contract Policy"}],
        "criteria": [
            {"criterion_id": "CRT-HBA1C", "requirement": "HbA1c above 8.0%", "mandatory": True, "required_evidence_keys": ["hba1c_report"], "clinical_rule": {"field": "clinical_metrics.hba1c", "operator": "gt", "value": 8.0}, "evidence_rule": {"field": "hba1c", "operator": "gt", "value": 8.0}},
        ],
    }

    provider = MockLLMProvider(response_generator=lambda _p, _s: json.dumps({"status": "MISSING", "selected_paths": [], "reason": ["HbA1c evidence is absent."]}))
    agent = DecisionAgent(llm_provider=provider)
    res = agent.evaluate_canonical_claim(build_canonical_claim(runtime_claim), build_rag_policy(runtime_policy))

    assert res.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
    assert res.criterion_assessments["CRT-HBA1C"].status == CriterionAssessmentStatus.MISSING
    assert res.criterion_assessments["CRT-HBA1C"].required_evidence_paths == ["hba1c_report"]


def test_runtime_transformation_conflicting_evidence_leads_to_human_review():
    """Conflicts remain evidence-only and are escalated to HUMAN_REVIEW without altering the deterministic policy engine."""
    runtime_claim = {
        "claim_id": "CLR-TRANS-004",
        "patient": {"patient_id": "PAT-TRANS-004", "age": 59, "gender": "Male"},
        "clinical_information": {
            "hba1c_report": {"status": "verified", "confidence_score": 0.95, "extracted_facts": {"hba1c": 8.4}},
            "hba1c_recheck": {"status": "verified", "confidence_score": 0.93, "extracted_facts": {"hba1c": 7.9}},
        },
        "submission": {"attempt": 1, "date": "2026-08-14"},
    }
    runtime_policy = {
        "claim_id": "CLR-TRANS-004",
        "matched_policies": [{"policy_id": "POL-TRANS-004", "name": "Runtime Contract Policy"}],
        "criteria": [
            {"criterion_id": "CRT-HBA1C", "requirement": "HbA1c above 8.0%", "mandatory": True, "required_evidence_keys": ["hba1c_report", "hba1c_recheck"], "clinical_rule": {"field": "clinical_metrics.hba1c", "operator": "gt", "value": 8.0}, "evidence_rule": {"field": "hba1c", "operator": "gt", "value": 8.0}},
        ],
    }

    provider = MockLLMProvider(response_generator=lambda _p, _s: json.dumps({"status": "CONFLICTING", "selected_paths": [1], "reason": ["Two lab values disagree materially."]}))
    agent = DecisionAgent(llm_provider=provider)
    res = agent.evaluate_canonical_claim(build_canonical_claim(runtime_claim), build_rag_policy(runtime_policy))

    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert res.criterion_assessments["CRT-HBA1C"].status == CriterionAssessmentStatus.CONFLICTING


def test_runtime_transformation_malformed_llm_output_fails_closed():
    """Malformed or invalid LLM output remains fail-closed even when using real transformation payloads."""
    runtime_claim = {
        "claim_id": "CLR-TRANS-005",
        "patient": {"patient_id": "PAT-TRANS-005", "age": 58, "gender": "Female"},
        "clinical_information": {"hba1c_report": {"status": "verified", "confidence_score": 0.95, "extracted_facts": {"hba1c": 9.1}}},
        "submission": {"attempt": 1, "date": "2026-08-14"},
    }
    runtime_policy = {
        "claim_id": "CLR-TRANS-005",
        "matched_policies": [{"policy_id": "POL-TRANS-005", "name": "Runtime Contract Policy"}],
        "criteria": [
            {"criterion_id": "CRT-HBA1C", "requirement": "HbA1c above 8.0%", "mandatory": True, "required_evidence_keys": ["hba1c_report"], "clinical_rule": {"field": "clinical_metrics.hba1c", "operator": "gt", "value": 8.0}, "evidence_rule": {"field": "hba1c", "operator": "gt", "value": 8.0}},
        ],
    }

    provider = MockLLMProvider(response_generator=lambda _p, _s: "not valid json")
    agent = DecisionAgent(llm_provider=provider)
    res = agent.evaluate_canonical_claim(build_canonical_claim(runtime_claim), build_rag_policy(runtime_policy))

    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert len(res.errors) > 0


def test_independence_verifications():
    """
    Ensure DecisionAgent does not import any database connection modules,
    raw Synthea files, or raw documents parser modules.

    The check runs in a fresh subprocess because third-party ML libraries
    (sentence_transformers/huggingface_hub via the RAG stack) transitively
    import sqlite3 into the shared pytest process, which would pollute a
    global sys.modules check without involving the decision layer at all.
    """
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    snippet = (
        "import sys\n"
        "import decision.agent\n"
        "import decision.decision_logic\n"
        "import decision.policy_evaluator\n"
        "import decision.evidence_evaluator\n"
        "bad = [m for m in ('sqlite3', 'psycopg2') if m in sys.modules]\n"
        "forbidden = ['synthea', 'database', 'db_client', 'raw_documents']\n"
        "bad += [m for m in sys.modules if any(f in m for f in forbidden)]\n"
        "print('|'.join(bad))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        cwd=str(root),
    )
    assert result.returncode == 0, f"Independence check crashed: {result.stderr}"
    bad_modules = result.stdout.strip()
    assert not bad_modules, f"Forbidden import found: {bad_modules}"
