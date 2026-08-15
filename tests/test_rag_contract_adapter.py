import pytest
from typing import Dict, Any

from adapters.rag_adapter import (
    rag_claim_adapter,
    rag_policy_adapter,
    CPT_MAP,
    DIAG_MAP,
)


def _get_mock_canonical_claim(
    claim_id: str = "CLM-TEST-001",
    payer: str = "Aetna",
    policy_id: str = "CPB-0660",
    procedures: list = None,
    diagnoses: list = None,
    evidence: list = None,
) -> Dict[str, Any]:
    if procedures is None:
        procedures = ["27447"]
    if diagnoses is None:
        diagnoses = ["M17.11"]
    if evidence is None:
        evidence = [
            {
                "evidence_key": "diagnosis",
                "evidence_id": "clinical_info_01",
                "source": "Clinical Information",
                "status": "verified",
                "confidence_score": 0.95,
                "extracted_facts": {"verified_facts": True},
            }
        ]
        
    return {
        "claim_id": claim_id,
        "submission": {"attempt": 1, "date": "2026-08-14T23:29:05Z"},
        "case_data": {
            "case_id": claim_id,
            "patient_age": 62,
            "diagnoses": diagnoses,
            "procedures": procedures,
            "clinical_metrics": {
                "patient_gender": "Female",
                "claim_scenario_type": "COMPLETE",
                "claim_payer": payer,
                "claim_policy_id": policy_id,
            },
        },
        "evidence": evidence,
    }


def test_payer_preservation_and_fail_safe():
    # 1. Payer is preserved as UNKNOWN and not defaulted to CMS
    claim_unknown = _get_mock_canonical_claim(payer="UNKNOWN", policy_id=None)
    inputs = rag_claim_adapter(claim_unknown)
    assert len(inputs) == 1
    assert inputs[0]["insurance"]["primary"]["payer"] == "UNKNOWN"
    assert inputs[0]["insurance"]["primary"]["policy_id"] is None
    
    # 2. Payer is completely missing/None
    claim_missing = _get_mock_canonical_claim(payer=None, policy_id=None)
    inputs_missing = rag_claim_adapter(claim_missing)
    assert len(inputs_missing) == 1
    assert inputs_missing[0]["insurance"]["primary"]["payer"] is None


def test_multiple_procedures_mapping():
    # Canonical Claim with multiple procedures ( TKA + THA )
    claim = _get_mock_canonical_claim(procedures=["27447", "27130"])
    inputs = rag_claim_adapter(claim)
    
    # Asserts that it produces exactly 2 RAG ClaimInput requests (Constraint 3 & 4)
    assert len(inputs) == 2
    assert inputs[0]["procedure"]["code"] == "27447"
    assert inputs[0]["clinical_domain"] == "orthopedics"
    assert inputs[1]["procedure"]["code"] == "27130"
    assert inputs[1]["clinical_domain"] == "orthopedics"


def test_canonical_to_rag_input_mapping():
    claim = _get_mock_canonical_claim()
    inputs = rag_claim_adapter(claim)
    
    assert len(inputs) == 1
    assert inputs[0]["claim_id"] == "CLM-TEST-001"
    assert inputs[0]["insurance"]["primary"]["payer"] == "Aetna"
    assert inputs[0]["insurance"]["primary"]["policy_id"] == "CPB-0660"
    assert len(inputs[0]["diagnosis"]) == 1
    assert inputs[0]["diagnosis"][0]["code"] == "M17.11"
    assert inputs[0]["diagnosis"][0]["description"] == "Primary osteoarthritis of right knee"
    assert inputs[0]["procedure"]["code"] == "27447"
    assert inputs[0]["procedure"]["description"] == "Total knee arthroplasty (TKA)"
    assert inputs[0]["clinical_domain"] == "orthopedics"


def test_rag_output_to_policy_mapping():
    canonical = _get_mock_canonical_claim()
    
    mock_rag_output = {
        "claim_id": "CLM-TEST-001",
        "policy_matches": [
            {"policy_id": "CPB-0660", "payer": "Aetna", "relevance_score": 0.89}
        ],
        "criteria": [
            {
                "criterion_id": "C01",
                "criterion": "Medical Necessity",
                "policy_requirement": "Total knee arthroplasty is medically necessary for adults...",
                "source": {"policy_id": "CPB-0660", "section": "Policy - Medical Necessity"}
            }
        ],
        "documentation_requirements": []
    }
    
    policy_dict = rag_policy_adapter(mock_rag_output, canonical)
    
    assert policy_dict["policy_id"] == "CPB-0660"
    assert policy_dict["name"] == "Aetna"
    assert len(policy_dict["criteria"]) == 1
    assert policy_dict["criteria"][0]["criterion_id"] == "C01"
    assert policy_dict["criteria"][0]["name"] == "Medical Necessity"
    assert policy_dict["criteria"][0]["description"] == "Total knee arthroplasty is medically necessary for adults..."
    assert policy_dict["criteria"][0]["mandatory"] is True


def test_criterion_specific_evidence_mapping():
    # Canonical Claim has specific evidence keys
    evidence = [
        {"evidence_key": "hba1c_report", "status": "verified", "confidence_score": 0.9},
        {"evidence_key": "bp_report", "status": "verified", "confidence_score": 0.8}
    ]
    canonical = _get_mock_canonical_claim(evidence=evidence)
    
    # RAG output criteria
    mock_rag_output = {
        "policy_matches": [{"policy_id": "POL-001", "payer": "Aetna"}],
        "criteria": [
            {
                "criterion_id": "CRT-HBA1C",
                "criterion": "HbA1c Check",
                "policy_requirement": "Check if HbA1c value is above 8.0%",
            },
            {
                "criterion_id": "CRT-BP",
                "criterion": "BP Check",
                "policy_requirement": "Verify blood pressure is stable",
            }
        ]
    }
    
    policy_dict = rag_policy_adapter(mock_rag_output, canonical)
    
    # Assert specific evidence keys are mapped to their respective criteria (Constraint 5 & 6)
    assert policy_dict["criteria"][0]["criterion_id"] == "CRT-HBA1C"
    assert policy_dict["criteria"][0]["required_evidence_keys"] == ["hba1c_report"]
    
    assert policy_dict["criteria"][1]["criterion_id"] == "CRT-BP"
    assert policy_dict["criteria"][1]["required_evidence_keys"] == ["bp_report"]


def test_known_rule_normalization():
    canonical = _get_mock_canonical_claim(policy_id="NCD-20.8.3")
    
    mock_rag_output = {
        "policy_matches": [{"policy_id": "NCD-20.8.3", "payer": "CMS"}],
        "criteria": [
            {
                "criterion_id": "C01",
                "criterion": "Pacemaker Necessity",
                "policy_requirement": "Covered for symptomatic bradycardia..."
            }
        ]
    }
    
    policy_dict = rag_policy_adapter(mock_rag_output, canonical)
    criterion = policy_dict["criteria"][0]
    
    # Assert registry maps rules correctly (Constraint 10)
    assert criterion["required_evidence_keys"] == ["diagnosis"]
    assert criterion["clinical_rule"] == {"field": "diagnoses", "operator": "contains", "value": "I49.5"}
    assert criterion["evidence_rule"] is None


def test_unresolved_rule_handling():
    canonical = _get_mock_canonical_claim(policy_id="UNKNOWN-POLICY")
    
    mock_rag_output = {
        "policy_matches": [{"policy_id": "UNKNOWN-POLICY", "payer": "Aetna"}],
        "criteria": [
            {
                "criterion_id": "C-99",
                "criterion": "Arbitrary Guideline",
                "policy_requirement": "Some random text requirement that has no clinical metrics pattern."
            }
        ]
    }
    
    policy_dict = rag_policy_adapter(mock_rag_output, canonical)
    criterion = policy_dict["criteria"][0]
    
    # Assert unmapped rules default to None/fail safely (Constraint 9 & 12)
    assert criterion["clinical_rule"] is None
    assert criterion["evidence_rule"] is None
    assert criterion["required_evidence_keys"] == ["__unresolved_rule_guard__"]


def test_provenance_preservation():
    canonical = _get_mock_canonical_claim()
    mock_rag_output = {
        "claim_id": "CLM-TEST-001",
        "policy_matches": [
            {"policy_id": "CPB-0660", "payer": "Aetna", "relevance_score": 0.89}
        ],
        "criteria": [
            {
                "criterion_id": "C01",
                "criterion": "Medical Necessity",
                "policy_requirement": "Total knee arthroplasty is medically necessary...",
                "source": {"policy_id": "CPB-0660", "section": "Policy - Medical Necessity"}
            }
        ]
    }
    
    policy_dict = rag_policy_adapter(mock_rag_output, canonical)
    
    # Verify provenance data is intact (Constraint 16)
    assert policy_dict["policy_id"] == "CPB-0660"
    assert policy_dict["matched_policies"][0]["policy_id"] == "CPB-0660"
    assert policy_dict["matched_policies"][0]["name"] == "Aetna"


# =====================================================================
# END-TO-END INTEGRATION TESTS (PHASE 4)
# =====================================================================

import json
from decision.schemas import DecisionOutcome, CriterionAssessmentStatus
from decision.llm_provider import MockLLMProvider
from services.integrated_pipeline import run_integrated_pipeline
from rag.query_builder.query_builder import QueryBuilder
from rag.retrieval.exact_matcher import ExactMatcher
from rag.retrieval.faiss_retriever import FAISSRetriever
from rag.retrieval.bm25_retriever import BM25Retriever
from rag.retrieval.candidate_pool import CandidatePool
from rag.reranking.bge_reranker import BGEReranker
from rag.aggregation.policy_aggregator import PolicyAggregator
from rag.analyzer.deterministic_analyzer import DeterministicAnalyzer
from rag.evidence.evidence_builder import EvidenceBuilder
from rag.llm.llm_client import LLMClient
from rag.llm.prompt_builder import PromptBuilder
from rag.validation.output_validator import OutputValidator


class GlobalMockRetriever:
    def __init__(self, matches=None):
        self.matches = matches or []
    def retrieve(self, *args, **kwargs):
        return self.matches
    def embed_query(self, *args, **kwargs):
        import numpy as np
        return np.zeros((768,), dtype=np.float32)


@pytest.fixture
def integration_components():
    """Build initialized components dictionary with Mock LLM Provider."""
    all_chunks = [
        {
            "chunk_id": "CMS-NCD-20.8.3-C01",
            "policy_id": "NCD-20.8.3",
            "payer": "CMS",
            "policy_title": "Permanent Cardiac Pacemakers",
            "clinical_domain": "cardiology",
            "procedure_codes": ["33206"],
            "diagnosis_codes": ["I49.5"],
            "section": "Coverage Criteria",
            "criterion_id": "C01",
            "criterion_type": "medical_necessity",
            "criterion_name": "Pacemaker Necessity",
            "text": "Covered for symptomatic bradycardia sinus node dysfunction (I49.5)."
        },
        {
            "chunk_id": "AETNA-CPB-0660-C01",
            "policy_id": "CPB-0660",
            "payer": "Aetna",
            "policy_title": "Total Knee Arthroplasty",
            "clinical_domain": "orthopedics",
            "procedure_codes": ["27447"],
            "diagnosis_codes": ["M17.11"],
            "section": "Policy - Medical Necessity",
            "criterion_id": "C01",
            "criterion_type": "medical_necessity",
            "criterion_name": "Knee Necessity",
            "text": "Total knee replacement is medically necessary for adults age >= 18."
        }
    ]
    all_chunks_dict = {c["chunk_id"]: c for c in all_chunks}
    
    exact = GlobalMockRetriever([])
    faiss = GlobalMockRetriever([{"chunk_id": "CMS-NCD-20.8.3-C01", "policy_id": "NCD-20.8.3", "score": 0.9}])
    bm25 = GlobalMockRetriever([])
    
    config = {
        "candidate_pool_size": 10
    }
    
    qb = QueryBuilder()
    pool = CandidatePool()
    
    class MockReranker:
        def rerank(self, query, candidates):
            for cand in candidates:
                cand["rerank_score"] = 0.95
            return candidates
            
    reranker = MockReranker()
    agg = PolicyAggregator()
    analyzer = DeterministicAnalyzer()
    eb = EvidenceBuilder()
    pb = PromptBuilder()
    validator = OutputValidator()
    
    class MockLLMClient:
        def generate_claim_output(self, claim_id, policy_id, payer, relevance_score, evidence_object, prompt=""):
            criteria = []
            for item in evidence_object.get("criteria", []):
                req_text = item.get("policy_requirement", "") if isinstance(item, dict) else str(item)
                criteria.append({
                    "criterion_id": "C01",
                    "criterion": "Pacemaker Necessity" if policy_id == "NCD-20.8.3" else "Knee Necessity",
                    "policy_requirement": req_text,
                    "source": {"policy_id": policy_id, "section": "Coverage Criteria"}
                })
            return {
                "claim_id": claim_id,
                "policy_matches": [
                    {"policy_id": policy_id, "payer": payer, "relevance_score": relevance_score}
                ],
                "criteria": criteria,
                "documentation_requirements": []
            }
            
        def _deterministic_formatter(self, claim_id, policy_id, payer, relevance_score, evidence_object):
            return self.generate_claim_output(claim_id, policy_id, payer, relevance_score, evidence_object)
            
    llm_client = MockLLMClient()
    
    return {
        "config": config,
        "all_chunks": all_chunks,
        "all_chunks_dict": all_chunks_dict,
        "exact_matcher": exact,
        "bge_embedder": GlobalMockRetriever(None),
        "faiss_retriever": faiss,
        "bm25_retriever": bm25,
        "candidate_pool": pool,
        "bge_reranker": reranker,
        "policy_aggregator": agg,
        "deterministic_analyzer": analyzer,
        "evidence_builder": eb,
        "llm_client": llm_client,
        "prompt_builder": pb,
        "output_validator": validator,
        "query_builder": qb,
        "llm_provider": None
    }


def test_e2e_normal_eligible_claim(integration_components):
    def response_gen(prompt, _system):
        payload = json.loads(prompt)
        selected = []
        for entry in payload.get("candidate_paths", []):
            try:
                selected.append(int(entry.split(":", 1)[0]))
            except Exception:
                pass
        return json.dumps({
            "status": "SUPPORTED",
            "selected_paths": selected,
            "reason": ["Evidence is present and verified."]
        })
        
    provider = MockLLMProvider(response_generator=response_gen)
    integration_components["llm_provider"] = provider
    
    canonical = _get_mock_canonical_claim(payer="CMS", policy_id="NCD-20.8.3", procedures=["33206"], diagnoses=["I49.5"])
    integration_components["faiss_retriever"] = GlobalMockRetriever([{"chunk_id": "CMS-NCD-20.8.3-C01", "policy_id": "NCD-20.8.3", "score": 0.9}])
    
    res = run_integrated_pipeline(canonical, integration_components)
    
    assert res.outcome == DecisionOutcome.APPROVE
    assert res.policy_id == "NCD-20.8.3"
    assert res.criterion_assessments["C01"].status == CriterionAssessmentStatus.SATISFIED


def test_e2e_failed_criterion(integration_components):
    def response_gen(prompt, _system):
        payload = json.loads(prompt)
        selected = []
        for entry in payload.get("candidate_paths", []):
            try:
                selected.append(int(entry.split(":", 1)[0]))
            except Exception:
                pass
        return json.dumps({
            "status": "SUPPORTED",
            "selected_paths": selected,
            "reason": ["Evidence is present but clinical threshold check will fail."]
        })
        
    provider = MockLLMProvider(response_generator=response_gen)
    integration_components["llm_provider"] = provider
    
    canonical = _get_mock_canonical_claim(payer="CMS", policy_id="NCD-20.8.3", procedures=["33206"], diagnoses=["I44.1"])
    integration_components["faiss_retriever"] = GlobalMockRetriever([{"chunk_id": "CMS-NCD-20.8.3-C01", "policy_id": "NCD-20.8.3", "score": 0.9}])
    
    res = run_integrated_pipeline(canonical, integration_components)
    
    assert res.outcome == DecisionOutcome.REJECT
    assert res.criteria_results["C01"] is False


def test_e2e_missing_documentation(integration_components):
    provider = MockLLMProvider(response_generator=lambda _p, _s: json.dumps({
        "status": "MISSING",
        "selected_paths": [],
        "reason": ["Required clinical information is missing."]
    }))
    integration_components["llm_provider"] = provider
    
    canonical = _get_mock_canonical_claim(payer="CMS", policy_id="NCD-20.8.3", procedures=["33206"], diagnoses=["I49.5"], evidence=[])
    integration_components["faiss_retriever"] = GlobalMockRetriever([{"chunk_id": "CMS-NCD-20.8.3-C01", "policy_id": "NCD-20.8.3", "score": 0.9}])
    
    res = run_integrated_pipeline(canonical, integration_components)
    
    assert res.outcome == DecisionOutcome.REQUEST_MORE_INFORMATION
    assert res.criterion_assessments["C01"].status == CriterionAssessmentStatus.MISSING


def test_e2e_conflicting_evidence(integration_components):
    provider = MockLLMProvider(response_generator=lambda _p, _s: json.dumps({
        "status": "CONFLICTING",
        "selected_paths": [],
        "reason": ["Evidence is contradictory."]
    }))
    integration_components["llm_provider"] = provider
    
    canonical = _get_mock_canonical_claim(payer="CMS", policy_id="NCD-20.8.3", procedures=["33206"], diagnoses=["I49.5"])
    integration_components["faiss_retriever"] = GlobalMockRetriever([{"chunk_id": "CMS-NCD-20.8.3-C01", "policy_id": "NCD-20.8.3", "score": 0.95}])
    
    res = run_integrated_pipeline(canonical, integration_components)
    
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert res.criterion_assessments["C01"].status == CriterionAssessmentStatus.CONFLICTING


def test_e2e_unknown_payer(integration_components):
    canonical = _get_mock_canonical_claim(payer="UNKNOWN", policy_id=None)
    
    res = run_integrated_pipeline(canonical, integration_components)
    
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW


def test_e2e_multiple_procedures(integration_components):
    canonical = _get_mock_canonical_claim(payer="Aetna", policy_id="CPB-0660", procedures=["27447", "27130"])
    integration_components["faiss_retriever"] = GlobalMockRetriever([{"chunk_id": "AETNA-CPB-0660-C01", "policy_id": "CPB-0660", "score": 0.9}])
    
    def response_gen(prompt, _system):
        payload = json.loads(prompt)
        selected = []
        for entry in payload.get("candidate_paths", []):
            try:
                selected.append(int(entry.split(":", 1)[0]))
            except Exception:
                pass
        return json.dumps({
            "status": "SUPPORTED",
            "selected_paths": selected,
            "reason": ["Evidence verified."]
        })
        
    provider = MockLLMProvider(response_generator=response_gen)
    integration_components["llm_provider"] = provider
    
    res = run_integrated_pipeline(canonical, integration_components)
    
    assert res.outcome == DecisionOutcome.APPROVE
    assert res.policy_id == "CPB-0660"


def test_e2e_rag_failure(integration_components):
    canonical = _get_mock_canonical_claim()
    
    integration_components["exact_matcher"] = None
    
    res = run_integrated_pipeline(canonical, integration_components)
    
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert any("RAG failed" in err or "critical error" in err.lower() for err in res.errors)


def test_e2e_malformed_unresolved_policy_output(integration_components):
    provider = MockLLMProvider(response_generator=lambda _p, _s: json.dumps({
        "status": "SUPPORTED",
        "selected_paths": [1],
        "reason": ["Grounded context looks valid."]
    }))
    integration_components["llm_provider"] = provider
    
    integration_components["all_chunks"] = [{"chunk_id": "UNKNOWN-C01", "policy_id": "UNKNOWN-POLICY", "payer": "Aetna", "criterion_id": "C01", "text": "Unresolvable text."}]
    integration_components["all_chunks_dict"] = {"UNKNOWN-C01": integration_components["all_chunks"][0]}
    integration_components["faiss_retriever"] = GlobalMockRetriever([{"chunk_id": "UNKNOWN-C01", "policy_id": "UNKNOWN-POLICY", "score": 0.95}])
    
    canonical = _get_mock_canonical_claim(payer="Aetna", policy_id="UNKNOWN-POLICY")
    
    res = run_integrated_pipeline(canonical, integration_components)
    
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW



