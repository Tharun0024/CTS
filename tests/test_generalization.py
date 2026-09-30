import os
import yaml
import pytest
from models.rag_models import ClaimInput
from rag.normalization.input_normalizer import normalize_claim_input
from rag.query_builder.query_builder import QueryBuilder
from rag.retrieval.exact_matcher import ExactMatcher
from rag.embeddings.bge_embedder import BGEEmbedder
from rag.retrieval.faiss_retriever import FAISSRetriever
from rag.retrieval.bm25_retriever import BM25Retriever
from rag.retrieval.candidate_pool import CandidatePool
from rag.reranking.bge_reranker import BGEReranker
from rag.aggregation.policy_aggregator import PolicyAggregator
import json

@pytest.fixture(scope="module")
def pipeline_components():
    config_path = os.path.join("config", "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    with open(config["paths"]["processed_chunks"], "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    chunks_dict = {c["chunk_id"]: c for c in chunks}
    
    # Init pipeline components
    qb = QueryBuilder()
    em = ExactMatcher(chunks)
    embedder = BGEEmbedder(model_name=config["embedding_model"], device=config["device"], cache_dir=config["paths"]["cache"])
    
    faiss_ret = FAISSRetriever(index_dir=config["paths"]["vector_store"])
    faiss_ret.load()
    
    bm25_ret = BM25Retriever(index_path=os.path.join(config["paths"]["vector_store"], "bm25.pkl"))
    bm25_ret.load()
    
    pool = CandidatePool()
    
    reranker = BGEReranker(model_name=config["reranker_model"], device=config["device"], cache_dir=config["paths"]["cache"])
    agg = PolicyAggregator()
    
    return {
        "chunks": chunks,
        "chunks_dict": chunks_dict,
        "qb": qb,
        "em": em,
        "embedder": embedder,
        "faiss": faiss_ret,
        "bm25": bm25_ret,
        "pool": pool,
        "reranker": reranker,
        "agg": agg,
        "config": config
    }

def run_retrieval_pipeline(claim: ClaimInput, pc) -> str:
    """
    Helper to execute standard retrieval pipeline matching a claim input.
    Returns the selected policy ID.
    """
    norm_claim = normalize_claim_input(claim)
    queries = pc["qb"].build_query(norm_claim)
    
    # 3-Way retrieval
    exact_res = pc["em"].retrieve(queries["structured"])
    q_vec = pc["embedder"].embed_query(queries["semantic_query"])
    faiss_res = pc["faiss"].retrieve(q_vec, top_k=pc["config"]["candidate_pool_size"])
    bm25_res = pc["bm25"].retrieve(queries["bm25_query"], top_k=pc["config"]["candidate_pool_size"])
    
    # Merging
    candidates = pc["pool"].merge(exact_res, faiss_res, bm25_res, pc["chunks_dict"])
    
    # Reranking
    reranked = pc["reranker"].rerank(queries["semantic_query"], candidates)
    
    # Aggregator
    selected_policy, _, _ = pc["agg"].aggregate(
        reranked,
        pc["chunks"],
        norm_claim.insurance.primary.payer,
        norm_claim.procedure.code,
        norm_claim.clinical_domain
    )
    return selected_policy

def test_semantic_generalization(pipeline_components):
    pc = pipeline_components
    
    # Test cases mapping knee replacement semantic descriptions
    semantic_tests = [
        "Complete replacement of the right knee due to degenerative arthritis.",
        "Right knee replacement for primary osteoarthritis.",
        "Surgical replacement of the affected right knee.",
        "Patient requires complete knee joint replacement due to OA."
    ]
    
    for query_desc in semantic_tests:
        claim = ClaimInput(
            claim_id="SEM-TEST",
            insurance={"primary": {"payer": "CMS", "policy_id": None}},
            diagnosis=[{"code": "M17.11", "description": "Osteoarthritis"}],
            procedure={"code": "27447", "description": query_desc},
            clinical_domain="orthopedics"
        )
        selected = run_retrieval_pipeline(claim, pc)
        # Should pick Knee policy LCD-L36575
        assert selected == "LCD-L36575", f"Failed semantic query: {query_desc}"

def test_syntactic_generalization(pipeline_components):
    pc = pipeline_components
    
    # Syntactic variation tests
    syntactic_tests = [
        "Right knee OA requiring total replacement.",
        "Total replacement of the right knee because of osteoarthritis.",
        "Patient has degenerative disease affecting the right knee and requires surgical joint replacement."
    ]
    
    for query_desc in syntactic_tests:
        claim = ClaimInput(
            claim_id="SYN-TEST",
            insurance={"primary": {"payer": "CMS (Medicare)", "policy_id": None}},
            diagnosis=[{"code": "M17.11", "description": "Osteoarthritis"}],
            procedure={"code": "27447", "description": query_desc},
            clinical_domain="orthopedics"
        )
        selected = run_retrieval_pipeline(claim, pc)
        assert selected == "LCD-L36575", f"Failed syntactic query: {query_desc}"

def test_hard_negatives(pipeline_components):
    pc = pipeline_components
    
    # Knee vs Hip: Correct policy must win!
    # Hip Claim
    hip_claim = ClaimInput(
        claim_id="HARD-NEG-HIP",
        insurance={"primary": {"payer": "CMS", "policy_id": None}},
        diagnosis=[{"code": "M16.11", "description": "Hip osteoarthritis"}],
        procedure={"code": "27130", "description": "Total hip arthroplasty"},
        clinical_domain="orthopedics"
    )
    selected_hip = run_retrieval_pipeline(hip_claim, pc)
    # Hip claim should retrieve LCD-L36039 (Total Joint Arthroplasty which covers hip)
    # and NOT the Knee policy LCD-L36575!
    assert selected_hip == "LCD-L36039"
    assert selected_hip != "LCD-L36575"
    
    # Knee Claim
    knee_claim = ClaimInput(
        claim_id="HARD-NEG-KNEE",
        insurance={"primary": {"payer": "CMS", "policy_id": None}},
        diagnosis=[{"code": "M17.11", "description": "Knee osteoarthritis"}],
        procedure={"code": "27447", "description": "Total knee arthroplasty"},
        clinical_domain="orthopedics"
    )
    selected_knee = run_retrieval_pipeline(knee_claim, pc)
    assert selected_knee == "LCD-L36575"

def test_missing_policy_id(pipeline_components):
    pc = pipeline_components
    
    # Remove policy ID: retrieval must still succeed using payer/procedure/domain/diagnoses
    claim = ClaimInput(
        claim_id="NO-POLICY-ID",
        insurance={"primary": {"payer": "CMS", "policy_id": None}},
        diagnosis=[{"code": "I49.5", "description": "Sinus node dysfunction"}],
        procedure={"code": "33206", "description": "Insertion of pacemaker"},
        clinical_domain="cardiology"
    )
    selected = run_retrieval_pipeline(claim, pc)
    assert selected == "NCD-20.8.3"

def test_conflict_case(pipeline_components):
    pc = pipeline_components
    
    # policy ID = pacemaker policy (NCD-20.8.3)
    # procedure = hip procedure (27130)
    # diagnosis = hip diagnosis (M16.11)
    claim = ClaimInput(
        claim_id="CONFLICT-TEST",
        insurance={"primary": {"payer": "CMS", "policy_id": "NCD-20.8.3"}},
        diagnosis=[{"code": "M16.11", "description": "Hip osteoarthritis"}],
        procedure={"code": "27130", "description": "Total hip arthroplasty"},
        clinical_domain="orthopedics"
    )
    selected = run_retrieval_pipeline(claim, pc)
    # The clinical procedure and domain (orthopedics) conflict with pacemaker (cardiology).
    # Since procedure and domain match Hip policy, the aggregator should align with LCD-L36039 (Hip)
    # or reject matching. In either case, it must NOT combine them or retrieve pacemaker info for hip.
    assert selected in ["LCD-L36039", "NO_RELIABLE_POLICY_MATCH"]
    assert selected != "NCD-20.8.3"

def test_unknown_case(pipeline_components):
    pc = pipeline_components
    
    # Completely unknown codes
    claim = ClaimInput(
        claim_id="UNKNOWN-TEST",
        insurance={"primary": {"payer": "CMS", "policy_id": None}},
        diagnosis=[{"code": "ZZ999", "description": "Unknown diagnosis"}],
        procedure={"code": "99999", "description": "Unknown procedure"},
        clinical_domain="neurology"
    )
    selected = run_retrieval_pipeline(claim, pc)
    assert selected == "NO_RELIABLE_POLICY_MATCH"
