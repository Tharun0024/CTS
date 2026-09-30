"""Focused Phase 5D regression tests for verified runtime gaps."""
import pytest

from adapters.runtime_adapter import RuntimeAdapter
from adapters.rag_adapter import rag_claim_adapter
from rag.aggregation.policy_aggregator import PolicyAggregator
from rag.llm.llm_client import LLMClient
from services.integrated_pipeline import run_integrated_pipeline
from decision.schemas import DecisionOutcome
from decision.llm_provider import MockLLMProvider
from tests.test_rag_contract_adapter import _get_mock_canonical_claim


def test_aggregator_rejects_domain_only_cross_procedure_match():
    """Hip policy must not be selected for a knee CPT even if domain matches."""
    agg = PolicyAggregator()
    hip_chunk = {
        "chunk_id": "AETNA-CPB-0287-C01",
        "policy_id": "CPB-0287",
        "payer": "Aetna",
        "policy_title": "Hip Arthroplasty",
        "procedure_codes": ["27130"],
        "clinical_domain": "orthopedics",
    }
    knee_chunk = {
        "chunk_id": "AETNA-CPB-0660-C01",
        "policy_id": "CPB-0660",
        "payer": "Aetna",
        "policy_title": "Knee Arthroplasty",
        "procedure_codes": ["27447"],
        "clinical_domain": "orthopedics",
    }
    candidates = [
        {"chunk": hip_chunk, "rerank_score": 0.99},
        {"chunk": knee_chunk, "rerank_score": 0.20},
    ]
    selected, chunks, _ = agg.aggregate(
        candidates,
        [hip_chunk, knee_chunk],
        query_payer="Aetna",
        query_proc="27447",
        query_domain="orthopedics",
    )
    assert selected == "CPB-0660"
    assert all(c["policy_id"] == "CPB-0660" for c in chunks)


def test_aggregator_fails_closed_when_requested_policy_missing():
    agg = PolicyAggregator()
    chunk = {
        "chunk_id": "AETNA-CPB-0660-C01",
        "policy_id": "CPB-0660",
        "payer": "Aetna",
        "procedure_codes": ["27447"],
        "clinical_domain": "orthopedics",
    }
    selected, chunks, score = agg.aggregate(
        [{"chunk": chunk, "rerank_score": 0.9}],
        [chunk],
        query_payer="Aetna",
        query_proc="27447",
        query_domain="orthopedics",
        requested_policy_id="LCD-L35074",
    )
    assert selected == "NO_RELIABLE_POLICY_MATCH"
    assert chunks == []
    assert score == 0.0


def test_aggregator_fails_closed_when_requested_policy_procedure_incompatible():
    agg = PolicyAggregator()
    hip = {
        "chunk_id": "AETNA-CPB-0287-C01",
        "policy_id": "CPB-0287",
        "payer": "Aetna",
        "procedure_codes": ["27130"],
        "clinical_domain": "orthopedics",
    }
    selected, chunks, _ = agg.aggregate(
        [{"chunk": hip, "rerank_score": 0.95}],
        [hip],
        query_payer="Aetna",
        query_proc="27447",
        query_domain="orthopedics",
        requested_policy_id="CPB-0287",
    )
    assert selected == "NO_RELIABLE_POLICY_MATCH"
    assert chunks == []


def test_runtime_diagnoses_are_claim_relevant_not_full_history():
    payload = RuntimeAdapter().get_provider_canonical_claim("PA045", "CLM-08BC25", 1)
    diagnoses = payload["case_data"]["diagnoses"]
    assert len(diagnoses) < 10
    assert "M17.11" in diagnoses or any(d.startswith("M17") for d in diagnoses)


def test_rag_claim_adapter_receives_payer_linkage_fields():
    linked = RuntimeAdapter().get_linked_runtime_claim("PA045", "CLM-08BC25", 1)
    inputs = rag_claim_adapter(linked)
    assert inputs[0]["insurance"]["primary"]["payer"] == "Aetna"
    metrics = linked["case_data"]["clinical_metrics"]
    assert metrics["member_id"] == "PA045"
    assert metrics["plan_id"] == "PLAN-CMS-001"
    assert metrics["claim_payer"] == "Aetna"
    assert metrics["claim_member_payer_mismatch"] is True


def test_llm_client_logs_auth_fallback_reason(monkeypatch, capsys):
    client = LLMClient()
    client.api_key = "sk-invalid-test-key-not-mock"
    client.api_url = "https://api.openai.com/v1"

    class FakeResp:
        status_code = 401
        text = '{"error":{"message":"Incorrect API key"}}'

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            return FakeResp()

    monkeypatch.setattr("rag.llm.llm_client.httpx.Client", FakeClient)
    out = client.generate_claim_output(
        "CLM-X",
        "CPB-0660",
        "Aetna",
        0.5,
        {"criteria": [], "documentation": []},
        prompt="{}",
    )
    assert out["claim_id"] == "CLM-X"
    assert client.last_fallback_reason == "llm_authentication_failed:http_401"
    captured = capsys.readouterr()
    assert "Deterministic fallback engaged" in captured.out
    assert "llm_authentication_failed:http_401" in captured.out


def test_integrated_pipeline_surfaces_payer_linkage(integration_components):
    """Payer context attached to claim appears in DecisionResponse reasoning."""
    import json

    claim = _get_mock_canonical_claim(
        payer="CMS",
        policy_id="NCD-20.8.3",
        procedures=["33206"],
        diagnoses=["I49.5"],
    )
    claim["case_data"]["clinical_metrics"].update(
        {
            "member_id": "PA045",
            "member_payer_id": "CMS",
            "plan_id": "PLAN-CMS-001",
            "eligibility_eligible": True,
            "claim_payer_normalized": "CMS",
            "member_payer_normalized": "CMS",
            "claim_member_payer_mismatch": False,
            "payer_alias_notes": [],
        }
    )

    def response_gen(prompt, _system):
        payload = json.loads(prompt)
        selected = []
        for entry in payload.get("candidate_paths", []):
            try:
                selected.append(int(entry.split(":", 1)[0]))
            except Exception:
                pass
        return json.dumps(
            {
                "status": "SUPPORTED",
                "selected_paths": selected,
                "reason": ["Evidence is present and verified."],
            }
        )

    integration_components["llm_provider"] = MockLLMProvider(response_generator=response_gen)
    integration_components["faiss_retriever"].matches = [
        {"chunk_id": "CMS-NCD-20.8.3-C01", "policy_id": "NCD-20.8.3", "score": 0.9}
    ]

    res = run_integrated_pipeline(claim, integration_components)
    assert res.outcome == DecisionOutcome.APPROVE
    joined = " ".join(res.reasoning)
    assert "Payer linkage" in joined
    assert "member_id=PA045" in joined
    assert "plan_id=PLAN-CMS-001" in joined


def test_integrated_pipeline_requested_missing_policy_fails_closed(integration_components):
    claim = _get_mock_canonical_claim(
        payer="Aetna",
        policy_id="LCD-L35074",
        procedures=["27447"],
        diagnoses=["M17.11"],
    )
    res = run_integrated_pipeline(claim, integration_components)
    assert res.outcome == DecisionOutcome.HUMAN_REVIEW
    assert any("RAG failed" in e for e in res.errors)


@pytest.fixture
def integration_components():
    return _build_integration_components()


def _build_integration_components():
    from tests.test_rag_contract_adapter import GlobalMockRetriever
    from rag.query_builder.query_builder import QueryBuilder
    from rag.retrieval.candidate_pool import CandidatePool
    from rag.aggregation.policy_aggregator import PolicyAggregator
    from rag.analyzer.deterministic_analyzer import DeterministicAnalyzer
    from rag.evidence.evidence_builder import EvidenceBuilder
    from rag.llm.prompt_builder import PromptBuilder
    from rag.validation.output_validator import OutputValidator

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
            "text": "Covered for symptomatic bradycardia sinus node dysfunction (I49.5).",
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
            "text": "Total knee replacement is medically necessary for adults age >= 18.",
        },
    ]
    all_chunks_dict = {c["chunk_id"]: c for c in all_chunks}

    class MockReranker:
        def rerank(self, query, candidates):
            for cand in candidates:
                cand["rerank_score"] = 0.95
            return candidates

    class MockLLMClient:
        def generate_claim_output(self, claim_id, policy_id, payer, relevance_score, evidence_object, prompt=""):
            criteria = []
            for item in evidence_object.get("criteria", []):
                req_text = item.get("policy_requirement", "") if isinstance(item, dict) else str(item)
                criteria.append(
                    {
                        "criterion_id": "C01",
                        "criterion": "Pacemaker Necessity" if policy_id == "NCD-20.8.3" else "Knee Necessity",
                        "policy_requirement": req_text,
                        "source": {"policy_id": policy_id, "section": "Coverage Criteria"},
                    }
                )
            return {
                "claim_id": claim_id,
                "policy_matches": [{"policy_id": policy_id, "payer": payer, "relevance_score": relevance_score}],
                "criteria": criteria,
                "documentation_requirements": [],
            }

        def _deterministic_formatter(self, claim_id, policy_id, payer, relevance_score, evidence_object):
            return self.generate_claim_output(claim_id, policy_id, payer, relevance_score, evidence_object)

    return {
        "config": {"candidate_pool_size": 10},
        "all_chunks": all_chunks,
        "all_chunks_dict": all_chunks_dict,
        "exact_matcher": GlobalMockRetriever([]),
        "bge_embedder": GlobalMockRetriever(None),
        "faiss_retriever": GlobalMockRetriever(
            [{"chunk_id": "CMS-NCD-20.8.3-C01", "policy_id": "NCD-20.8.3", "score": 0.9}]
        ),
        "bm25_retriever": GlobalMockRetriever([]),
        "candidate_pool": CandidatePool(),
        "bge_reranker": MockReranker(),
        "policy_aggregator": PolicyAggregator(),
        "deterministic_analyzer": DeterministicAnalyzer(),
        "evidence_builder": EvidenceBuilder(),
        "llm_client": MockLLMClient(),
        "prompt_builder": PromptBuilder(),
        "output_validator": OutputValidator(),
        "query_builder": QueryBuilder(),
        "llm_provider": None,
    }
