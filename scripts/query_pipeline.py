import os
import sys
import yaml
import json
import argparse

# Direct imports from src
from src.schema.models import ClaimInput
from src.normalization.input_normalizer import normalize_claim_input
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
from src.llm.prompt_builder import PromptBuilder
from src.validation.output_validator import OutputValidator

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Overwrite api key/url from environment if set
    config["llm"]["api_key"] = os.getenv("LLM_API_KEY", config["llm"]["api_key"])
    config["llm"]["api_url"] = os.getenv("LLM_API_URL", config["llm"]["api_url"])
    return config

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
    chunks_path = os.path.join(config["paths"]["processed"], "chunks.json")
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
        index_dir=config["paths"]["vector_store"],
        device=config["device"]
    )
    bm25_retriever = BM25Retriever(
        index_dir=config["paths"]["vector_store"]
    )
    candidate_pool = CandidatePool()
    reranker = BGEReranker(
        model_name=config["reranker_model"],
        device=config["device"],
        cache_dir=config["paths"]["cache"]
    )
    aggregator = PolicyAggregator(boost_weight=config["aggregation"]["specificity_boost"])
    evidence_builder = EvidenceBuilder()
    analyzer = DeterministicAnalyzer()
    llm_client = LLMClient(api_key=config["llm"]["api_key"], api_url=config["llm"]["api_url"])
    validator = OutputValidator()
    
    print("\nRunning model pipeline...")
    # 1. Normalize Input
    norm_claim = normalize_claim_input(claim_data)
    
    # 2. Exact Match
    exact_matches = exact_matcher.match_claim(norm_claim)
    
    # 3. Dense & Sparse Retrieval
    query_builder = QueryBuilder()
    query_dict = query_builder.build_queries(norm_claim)
    
    query_emb = embedder.embed_query(query_dict["semantic_query"])
    faiss_matches = faiss_retriever.search(query_emb, k=10)
    dense_results = [(all_chunks_dict[chunk_id], score) for chunk_id, score in faiss_matches]
    
    bm25_matches = bm25_retriever.search(query_dict["semantic_query"], k=10)
    sparse_results = [(all_chunks_dict[chunk_id], score) for chunk_id, score in bm25_matches]
    
    # 4. Merge
    candidates = candidate_pool.merge_candidates(exact_matches, dense_results, sparse_results)
    
    # 5. Rerank
    reranked = reranker.rerank(query_dict["semantic_query"], candidates)
    
    # 6. Aggregate
    aggregated_policy, final_candidates = aggregator.aggregate(query_dict["cpt_codes"], reranked)
    
    # 7. Evidence
    evidence = evidence_builder.build_evidence(aggregated_policy, final_candidates)
    
    # 8. Analyze
    decision = analyzer.analyze_claim(norm_claim, evidence)
    
    # 9. LLM verification/synthesis
    print("Generating decision using LLM verification...")
    llm_response = llm_client.generate_decision(
        claim_id=norm_claim.claim_id,
        policy_id=aggregated_policy,
        payer=norm_claim.insurance.primary.payer,
        relevance_score=evidence.relevance_score if evidence else 0.0,
        evidence_object=evidence
    )
    
    # 10. Validate
    validated_output = validator.validate(llm_response)
    
    print("\n================== PIPELINE OUTPUT ==================")
    print(json.dumps(validated_output, indent=2))
    print("=====================================================")

if __name__ == "__main__":
    main()
