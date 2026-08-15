import os
import json
import numpy as np
import pytest
import yaml

from src.schema.models import ClaimInput, ClaimOutput
from src.normalization.input_normalizer import normalize_claim_input, normalize_payer_name, normalize_policy_id
from src.query_builder.query_builder import QueryBuilder
from src.retrieval.exact_matcher import ExactMatcher
from src.embeddings.bge_embedder import BGEEmbedder
from src.retrieval.faiss_retriever import FAISSRetriever
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.candidate_pool import CandidatePool
from src.reranking.bge_reranker import BGEReranker
from src.aggregation.policy_aggregator import PolicyAggregator
from src.analyzer.deterministic_analyzer import DeterministicAnalyzer
from src.evidence.evidence_builder import EvidenceBuilder
from src.llm.llm_client import LLMClient
from src.validation.output_validator import OutputValidator

@pytest.fixture(scope="module")
def config():
    config_path = os.path.join("config", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="module")
def sample_claim():
    return ClaimInput(
        claim_id="CLM-TEST-001",
        insurance={
            "primary": {
                "payer": "medicare",
                "policy_id": "lcd-l36575"
            }
        },
        diagnosis=[
            {"code": "M17.11", "description": "Right knee osteoarthritis"}
        ],
        procedure={
            "code": "27447",
            "description": "Total knee arthroplasty"
        },
        clinical_domain="orthopedics"
    )

@pytest.fixture(scope="module")
def processed_chunks(config):
    processed_path = config["paths"]["processed_chunks"]
    with open(processed_path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_normalization(sample_claim):
    # Test normalization of payer name
    assert normalize_payer_name("cms medicare") == "CMS (Medicare)"
    assert normalize_payer_name("AETNA INC") == "Aetna"
    
    # Test normalization of Policy ID
    assert normalize_policy_id("cpb0660") == "CPB-0660"
    
    # Test overall claim normalization
    norm_claim = normalize_claim_input(sample_claim)
    assert norm_claim.insurance.primary.payer == "CMS (Medicare)"
    assert norm_claim.insurance.primary.policy_id == "LCD-L36575"
    assert norm_claim.clinical_domain == "orthopedics"

def test_query_builder(sample_claim):
    qb = QueryBuilder()
    norm_claim = normalize_claim_input(sample_claim)
    queries = qb.build_query(norm_claim)
    
    assert "structured" in queries
    assert "exact_tokens" in queries
    assert "bm25_query" in queries
    assert "semantic_query" in queries
    
    # Verify exact tokens contain normalized procedure and diagnoses
    assert "27447" in queries["exact_tokens"]
    assert "m17.11" in queries["exact_tokens"]

def test_exact_matcher(processed_chunks):
    em = ExactMatcher(processed_chunks)
    
    # Matching query
    query = {
        "payer": "CMS (Medicare)",
        "policy_id": "LCD-L36575",
        "clinical_domain": "orthopedics",
        "procedure_code": "27447",
        "diagnosis_codes": ["M17.11"]
    }
    
    matches = em.retrieve(query, top_k=5)
    assert len(matches) > 0
    # Check that highest scoring matches correspond to the correct policy
    assert matches[0]["chunk"]["policy_id"] == "LCD-L36575"
    assert matches[0]["score"] > 0.8

def test_bge_embedder(config):
    embedder = BGEEmbedder(
        model_name=config["embedding_model"],
        device=config["device"],
        cache_dir=config["paths"]["cache"]
    )
    # Test query embedding
    q_vec = embedder.embed_query("test clinical query")
    assert isinstance(q_vec, np.ndarray)
    assert q_vec.shape == (768,)
    
    # Test normal similarity
    q2_vec = embedder.embed_query("test clinical search")
    sim = np.dot(q_vec, q2_vec)
    # Norm is 1.0 since it normalizes internally
    assert 0.0 <= sim <= 1.01

def test_faiss_retriever(config):
    fr = FAISSRetriever(index_dir=config["paths"]["vector_store"])
    fr.load()
    
    # Retrieve using a dummy random vector
    dummy_vec = np.random.rand(768).astype("float32")
    # Normalize dummy vector
    dummy_vec /= np.linalg.norm(dummy_vec)
    
    res = fr.retrieve(dummy_vec, top_k=5)
    assert len(res) == 5
    assert "chunk_id" in res[0]
    assert "score" in res[0]

def test_bm25_retriever(config):
    bm25 = BM25Retriever(index_path=os.path.join(config["paths"]["vector_store"], "bm25.pkl"))
    bm25.load()
    
    res = bm25.retrieve("mammogram screening breast cancer", top_k=5)
    assert len(res) > 0
    assert "chunk_id" in res[0]
    assert res[0]["score"] <= 1.0

def test_candidate_pool(processed_chunks):
    pool = CandidatePool()
    chunks_dict = {c["chunk_id"]: c for c in processed_chunks}
    
    exact_matches = [{"chunk": processed_chunks[0], "score": 0.9}]
    faiss_matches = [{"chunk_id": processed_chunks[0]["chunk_id"], "policy_id": processed_chunks[0]["policy_id"], "score": 0.8}]
    bm25_matches = [{"chunk_id": processed_chunks[0]["chunk_id"], "policy_id": processed_chunks[0]["policy_id"], "score": 0.7}]
    
    merged = pool.merge(exact_matches, faiss_matches, bm25_matches, chunks_dict)
    assert len(merged) == 1
    assert merged[0]["chunk_id"] == processed_chunks[0]["chunk_id"]
    # Check weighted score: 0.5*0.9 + 0.3*0.8 + 0.2*0.7 = 0.45 + 0.24 + 0.14 = 0.83
    assert abs(merged[0]["combined_score"] - 0.83) < 1e-5

def test_policy_aggregator_and_gate(processed_chunks):
    agg = PolicyAggregator()
    
    # Mock candidates
    candidates = [
        {
            "chunk_id": "CMS-NCD-20.8.3-C01",
            "policy_id": "NCD-20.8.3",
            "chunk": {
                "chunk_id": "CMS-NCD-20.8.3-C01",
                "policy_id": "NCD-20.8.3",
                "payer": "CMS (Medicare)",
                "procedure_codes": ["33206"],
                "clinical_domain": "cardiology"
            },
            "combined_score": 0.9
        },
        {
            "chunk_id": "CMS-LCD-L36575-C01",
            "policy_id": "LCD-L36575",
            "chunk": {
                "chunk_id": "CMS-LCD-L36575-C01",
                "policy_id": "LCD-L36575",
                "payer": "CMS (Medicare)",
                "procedure_codes": ["27447"],
                "clinical_domain": "orthopedics"
            },
            "combined_score": 0.8
        }
    ]
    
    selected_policy, chunks, score = agg.aggregate(
        candidates,
        processed_chunks,
        query_payer="CMS (Medicare)",
        query_proc="27447",
        query_domain="orthopedics"
    )
    
    # Should pick LCD-L36575 because procedure code '27447' matches clinically,
    # despite NCD-20.8.3 having a higher combined retrieval score.
    assert selected_policy == "LCD-L36575"
    assert len(chunks) > 0
    
    # Policy Consistency Gate Check: Ensure 0% cross-contamination rate
    for chunk in chunks:
        assert chunk["policy_id"] == "LCD-L36575"

def test_deterministic_analyzer_and_evidence():
    analyzer = DeterministicAnalyzer()
    eb = EvidenceBuilder()
    
    # Dummy chunk list for a policy
    policy_chunks = [
        {
            "chunk_id": "CMS-TEST-C01",
            "policy_id": "TEST-POLICY",
            "payer": "CMS (Medicare)",
            "section": "Coverage Criteria",
            "criterion_id": "C01",
            "criterion_name": "Test — medical necessity criteria",
            "text": "Medically necessary when patient has pain. Excludes patients with infection.",
            "documentation_requirements": ["Clinical documentation"],
            "exclusions": ["infection"],
            "limitations": ["unilateral only"]
        }
    ]
    
    result = analyzer.analyze_chunks(policy_chunks)
    assert len(result["criteria"]) == 1
    assert result["criteria"][0]["criterion_id"] == "C01"
    # Verify no decision variables (approve/reject/met) exist in output
    for c in result["criteria"]:
        assert "met" not in c
        assert "decision" not in c
        
    evidence = eb.build_evidence("TEST-POLICY", "CMS (Medicare)", result, policy_chunks)
    assert evidence["policy_id"] == "TEST-POLICY"
    assert len(evidence["criteria"]) == 1
    assert len(evidence["documentation"]) == 1
    assert "infection" in evidence["exclusions"]
