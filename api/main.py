import os
import time
import yaml
import json
from fastapi import FastAPI, HTTPException, Query
from pydantic import ValidationError
from typing import Dict, Any

from src.schema.models import ClaimInput, ClaimOutput
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

app = FastAPI(
    title="Generalized Prior Authorization Policy Retrieval RAG API",
    description="A semantic policy search and structured criteria extraction engine.",
    version="1.0.0"
)

# Global variables to cache loaded models and indexes
CONFIG: Dict[str, Any] = {}
ALL_CHUNKS: list = []
ALL_CHUNKS_DICT: Dict[str, Dict[str, Any]] = {}
EXACT_MATCHER: ExactMatcher = None
BGE_EMBEDDER: BGEEmbedder = None
FAISS_RETRIEVER: FAISSRetriever = None
BM25_RETRIEVER: BM25Retriever = None
CANDIDATE_POOL: CandidatePool = None
BGE_RERANKER: BGEReranker = None
POLICY_AGGREGATOR: PolicyAggregator = None
DETERMINISTIC_ANALYZER: DeterministicAnalyzer = None
EVIDENCE_BUILDER: EvidenceBuilder = None
LLM_CLIENT: LLMClient = None
PROMPT_BUILDER: PromptBuilder = None
OUTPUT_VALIDATOR: OutputValidator = None
QUERY_BUILDER: QueryBuilder = None

@app.on_event("startup")
def startup_event():
    global CONFIG, ALL_CHUNKS, ALL_CHUNKS_DICT, EXACT_MATCHER, BGE_EMBEDDER
    global FAISS_RETRIEVER, BM25_RETRIEVER, CANDIDATE_POOL, BGE_RERANKER
    global POLICY_AGGREGATOR, DETERMINISTIC_ANALYZER, EVIDENCE_BUILDER
    global LLM_CLIENT, PROMPT_BUILDER, OUTPUT_VALIDATOR, QUERY_BUILDER
    
    print("Initializing RAG API and loading indexes/models...")
    
    # 1. Load config
    config_path = os.path.join("config", "config.yaml")
    with open(config_path, "r") as f:
        CONFIG = yaml.safe_load(f)
        
    # 2. Load chunk database
    processed_chunks_path = CONFIG["paths"]["processed_chunks"]
    if not os.path.exists(processed_chunks_path):
        raise FileNotFoundError(f"Processed chunks not found at {processed_chunks_path}. Please run index builder script first.")
        
    with open(processed_chunks_path, "r", encoding="utf-8") as f:
        ALL_CHUNKS = json.load(f)
    ALL_CHUNKS_DICT = {c["chunk_id"]: c for c in ALL_CHUNKS}
    
    # 3. Instantiate Matchers and Retrievers
    EXACT_MATCHER = ExactMatcher(ALL_CHUNKS)
    
    # Embedder (sentence-transformers)
    BGE_EMBEDDER = BGEEmbedder(
        model_name=CONFIG["embedding_model"],
        device=CONFIG["device"],
        cache_dir=CONFIG["paths"]["cache"]
    )
    
    # FAISS Retriever
    FAISS_RETRIEVER = FAISSRetriever(
        index_dir=CONFIG["paths"]["vector_store"]
    )
    FAISS_RETRIEVER.load()
    
    # BM25 Retriever
    BM25_RETRIEVER = BM25Retriever(
        index_path=os.path.join(CONFIG["paths"]["vector_store"], "bm25.pkl")
    )
    BM25_RETRIEVER.load()
    
    # Candidate Pool
    CANDIDATE_POOL = CandidatePool()
    
    # BGE Reranker (AutoModelForSequenceClassification)
    print("Loading Reranker model (this might take a few seconds on first run)...")
    BGE_RERANKER = BGEReranker(
        model_name=CONFIG["reranker_model"],
        device=CONFIG["device"],
        cache_dir=CONFIG["paths"]["cache"]
    )
    
    # Other pipeline elements
    POLICY_AGGREGATOR = PolicyAggregator()
    DETERMINISTIC_ANALYZER = DeterministicAnalyzer()
    EVIDENCE_BUILDER = EvidenceBuilder()
    LLM_CLIENT = LLMClient()
    PROMPT_BUILDER = PromptBuilder()
    OUTPUT_VALIDATOR = OutputValidator()
    QUERY_BUILDER = QueryBuilder()
    
    print("RAG API initialization successfully completed.")

@app.post("/triage", response_model=ClaimOutput)
def triage(claim_input: ClaimInput, debug: bool = Query(False, description="Enable return of debug details in logs")):
    """
    POST /triage
    Executes the structured three-way RAG policy retrieval and requirement extraction pipeline.
    """
    try:
        start_time = time.time()
        
        # 1. Input Normalization
        norm_claim = normalize_claim_input(claim_input)
        
        # 2. Query Builder
        queries = QUERY_BUILDER.build_query(norm_claim)
        
        # 3. Three-Way Retrieval
        # Exact Matching
        exact_matches = EXACT_MATCHER.retrieve(queries["structured"])
        
        # BGE/FAISS Semantic
        query_vector = BGE_EMBEDDER.embed_query(queries["semantic_query"])
        faiss_matches = FAISS_RETRIEVER.retrieve(query_vector, top_k=CONFIG["candidate_pool_size"])
        
        # BM25 Keyword Search
        bm25_matches = BM25_RETRIEVER.retrieve(queries["bm25_query"], top_k=CONFIG["candidate_pool_size"])
        
        # 4. Candidate Pool Merging (Top 10)
        top_candidates = CANDIDATE_POOL.merge(
            exact_matches,
            faiss_matches,
            bm25_matches,
            ALL_CHUNKS_DICT
        )
        
        # 5. Reranking (BGE Reranker V2 M3)
        reranked_candidates = BGE_RERANKER.rerank(queries["semantic_query"], top_candidates)
        
        # 6. Policy Aggregator & Consistency Gate
        selected_policy_id, aggregated_chunks, best_score = POLICY_AGGREGATOR.aggregate(
            reranked_candidates,
            ALL_CHUNKS,
            norm_claim.insurance.primary.payer,
            norm_claim.procedure.code,
            norm_claim.clinical_domain
        )
        
        # 7. Deterministic Analyzer
        analyzer_output = DETERMINISTIC_ANALYZER.analyze_chunks(aggregated_chunks)
        
        # 8. Evidence Object
        evidence_object = EVIDENCE_BUILDER.build_evidence(
            selected_policy_id,
            norm_claim.insurance.primary.payer,
            analyzer_output,
            aggregated_chunks
        )
        
        # 9. LLM Generation
        prompt = PROMPT_BUILDER.build_prompt(norm_claim.dict(), evidence_object)
        final_output = LLM_CLIENT.generate_claim_output(
            claim_id=norm_claim.claim_id,
            policy_id=selected_policy_id,
            payer=norm_claim.insurance.primary.payer,
            relevance_score=best_score,
            evidence_object=evidence_object,
            prompt=prompt
        )
        
        # 10. Clean disallowed keys & Validate JSON Schema
        cleaned_output = OUTPUT_VALIDATOR.filter_decision_fields(final_output)
        is_valid = OUTPUT_VALIDATOR.validate(cleaned_output, selected_policy_id)
        
        if not is_valid:
            # Fallback format to guarantee validation passes
            if os.getenv("DEBUG", "false").lower() == "true" or debug:
                print("[API] Output validation failed. Triggering recovery formatting.")
            recovery_output = LLM_CLIENT._deterministic_formatter(
                claim_id=norm_claim.claim_id,
                policy_id=selected_policy_id,
                payer=norm_claim.insurance.primary.payer,
                relevance_score=best_score,
                evidence_object=evidence_object
            )
            cleaned_output = OUTPUT_VALIDATOR.filter_decision_fields(recovery_output)
            
        latency = (time.time() - start_time) * 1000
        
        # Log debug details if requested
        if os.getenv("DEBUG", "false").lower() == "true" or debug:
            print(f"================= DEBUG FOR {claim_input.claim_id} =================")
            print(f"Normalized claim: {norm_claim}")
            print(f"Generated queries: {queries}")
            print(f"Selected Policy ID: {selected_policy_id} (Score: {best_score})")
            print(f"Total Aggregated Chunks: {len(aggregated_chunks)}")
            print(f"Total Pipeline Latency: {latency:.2f} ms")
            print("==================================================================")
            
        return cleaned_output
        
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=f"Validation Error: {ve.errors()}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
