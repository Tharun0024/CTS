import os
import sys
import yaml
import json
import argparse

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
from rag.analyzer.deterministic_analyzer import DeterministicAnalyzer
from rag.evidence.evidence_builder import EvidenceBuilder
from rag.llm.llm_client import LLMClient
from rag.llm.prompt_builder import PromptBuilder
from rag.validation.output_validator import OutputValidator

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description="Query the Prior Authorization Policy Retrieval RAG Model Pipeline.")
    parser.add_argument("claim_file", help="Path to the JSON file containing the claim input payload.")
    args = parser.parse_args()
    
    if not os.path.exists(args.claim_file):
        print(f"Error: Claim file not found at '{args.claim_file}'")
        sys.exit(1)
        
    try:
        with open(args.claim_file, "r") as f:
            claim_data = json.load(f)
    except Exception as e:
        print(f"Error parsing JSON from '{args.claim_file}': {e}")
        sys.exit(1)
        
    print("Loading configuration...")
    config = load_config()
    
    print("Initializing RAG pipeline components...")
    # Load chunks metadata
    chunks_path = config["paths"]["processed_chunks"]
    with open(chunks_path, "r") as f:
        all_chunks = json.load(f)
    all_chunks_dict = {c["chunk_id"]: c for c in all_chunks}
    
    # Initialize components
    exact_matcher = ExactMatcher(all_chunks)
    embedder = BGEEmbedder(
        model_name=config["embedding_model"],
        device=config["device"],
        cache_dir=config["paths"]["cache"]
    )
    faiss_retriever = FAISSRetriever(
        index_dir=config["paths"]["vector_store"]
    )
    faiss_retriever.load()
    bm25_retriever = BM25Retriever(
        index_path=os.path.join(config["paths"]["vector_store"], "bm25.pkl")
    )
    bm25_retriever.load()
    candidate_pool = CandidatePool()
    reranker = BGEReranker(
        model_name=config["reranker_model"],
        device=config["device"],
        cache_dir=config["paths"]["cache"]
    )
    aggregator = PolicyAggregator()
    evidence_builder = EvidenceBuilder()
    analyzer = DeterministicAnalyzer()
    llm_client = LLMClient()
    prompt_builder = PromptBuilder()
    validator = OutputValidator()
    query_builder = QueryBuilder()
    
    print("\nRunning model pipeline...")
    # Initialize components dictionary
    components = {
        "config": config,
        "all_chunks": all_chunks,
        "all_chunks_dict": all_chunks_dict,
        "exact_matcher": exact_matcher,
        "bge_embedder": embedder,
        "faiss_retriever": faiss_retriever,
        "bm25_retriever": bm25_retriever,
        "candidate_pool": candidate_pool,
        "bge_reranker": reranker,
        "policy_aggregator": aggregator,
        "deterministic_analyzer": analyzer,
        "evidence_builder": evidence_builder,
        "llm_client": llm_client,
        "prompt_builder": prompt_builder,
        "output_validator": validator,
        "query_builder": query_builder
    }
    
    # 1. Convert input to Canonical Claim using runtime adapter helper
    from transformation.canonical_claim import build_canonical_claim
    from adapters.runtime_adapter import RuntimeAdapter

    # If the payload already carries provider case_data, keep it; otherwise normalize.
    # When patient_id is present, optionally enrich with payer linkage (never overrides claim_payer).
    canonical_claim = build_canonical_claim(claim_data)
    patient_id = None
    if isinstance(claim_data.get("patient"), dict):
        patient_id = claim_data["patient"].get("patient_id")
    patient_id = patient_id or (claim_data.get("case_data") or {}).get("clinical_metrics", {}).get("member_id")
    if patient_id and "payer_context" not in canonical_claim:
        adapter = RuntimeAdapter()
        payer_ctx = adapter.get_payer_context(patient_id)
        canonical_claim = adapter.attach_payer_context(canonical_claim, payer_ctx)
    
    # 2. Run the end-to-end integrated pipeline
    from services.integrated_pipeline import run_integrated_pipeline
    decision_response = run_integrated_pipeline(canonical_claim, components)
    
    print("\n================== PIPELINE OUTPUT ==================")
    print(json.dumps(decision_response.model_dump(mode="json"), indent=2))
    print("=====================================================")

if __name__ == "__main__":
    main()

