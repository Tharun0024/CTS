import os
import time
import json
import yaml
import numpy as np
import subprocess
from typing import Dict, Any, List

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

def get_memory_usage_mb() -> float:
    """
    Get RSS memory usage of the current process in MB.
    Uses psutil if available, falls back to Windows tasklist utility.
    """
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        try:
            pid = os.getpid()
            cmd = f'tasklist /FI "PID eq {pid}" /FO CSV'
            output = subprocess.check_output(cmd, shell=True).decode('utf-8')
            lines = output.strip().split("\n")
            if len(lines) >= 2:
                parts = lines[1].split(",")
                if len(parts) >= 5:
                    mem_str = parts[4].replace('"', '').replace(' K', '').replace(',', '').strip()
                    return float(mem_str) / 1024.0
        except Exception:
            pass
        return 0.0

def main():
    print("=====================================================")
    print("STARTING BENCHMARK FOR PRIOR AUTHORIZATION RAG SYSTEM")
    print("=====================================================")
    
    mem_start = get_memory_usage_mb()
    print(f"Initial Memory Usage: {mem_start:.2f} MB")
    
    # 1. Load config
    config_path = os.path.join("config", "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    # 2. Load chunk database
    processed_chunks_path = config["paths"]["processed_chunks"]
    with open(processed_chunks_path, "r", encoding="utf-8") as f:
        all_chunks = json.load(f)
    all_chunks_dict = {c["chunk_id"]: c for c in all_chunks}
    
    # 3. Instantiate pipeline elements (measure loading memory/time)
    t_load_start = time.time()
    
    qb = QueryBuilder()
    em = ExactMatcher(all_chunks)
    embedder = BGEEmbedder(
        model_name=config["embedding_model"],
        device=config["device"],
        cache_dir=config["paths"]["cache"]
    )
    
    faiss_ret = FAISSRetriever(index_dir=config["paths"]["vector_store"])
    faiss_ret.load()
    
    bm25_ret = BM25Retriever(index_path=os.path.join(config["paths"]["vector_store"], "bm25.pkl"))
    bm25_ret.load()
    
    pool = CandidatePool()
    
    reranker = BGEReranker(
        model_name=config["reranker_model"],
        device=config["device"],
        cache_dir=config["paths"]["cache"]
    )
    
    agg = PolicyAggregator()
    analyzer = DeterministicAnalyzer()
    eb = EvidenceBuilder()
    llm = LLMClient()
    prompt_builder = PromptBuilder()
    validator = OutputValidator()
    
    t_load_end = time.time()
    mem_loaded = get_memory_usage_mb()
    
    load_time_sec = t_load_end - t_load_start
    model_memory_mb = mem_loaded - mem_start
    
    print(f"Components loaded in: {load_time_sec:.2f} seconds")
    print(f"Memory after loading components: {mem_loaded:.2f} MB (Delta: {model_memory_mb:.2f} MB)")
    
    # Define benchmark claim
    benchmark_claim_raw = {
        "claim_id": "BENCHMARK-001",
        "insurance": {
            "primary": {
                "payer": "CMS",
                "policy_id": None
            }
        },
        "diagnosis": [
            {"code": "I49.5", "description": "Sick sinus syndrome"}
        ],
        "procedure": {
            "code": "33206",
            "description": "Insertion of pacemaker"
        },
        "clinical_domain": "cardiology"
    }
    
    claim_input = ClaimInput(**benchmark_claim_raw)
    
    # Component latency accumulators
    latencies = {
        "normalization": [],
        "query_builder": [],
        "exact_matching": [],
        "embedding": [],
        "faiss_retrieval": [],
        "bm25_retrieval": [],
        "merging": [],
        "reranking": [],
        "aggregation": [],
        "deterministic_analysis": [],
        "evidence_building": [],
        "llm_generation": [],
        "validation": [],
        "total_pipeline": []
    }
    
    print("\nRunning warm-up pipeline execution...")
    # Warmup
    norm_claim = normalize_claim_input(claim_input)
    queries = qb.build_query(norm_claim)
    exact_matches = em.retrieve(queries["structured"])
    q_vec = embedder.embed_query(queries["semantic_query"])
    faiss_matches = faiss_ret.retrieve(q_vec, top_k=config["candidate_pool_size"])
    bm25_matches = bm25_ret.retrieve(queries["bm25_query"], top_k=config["candidate_pool_size"])
    top_candidates = pool.merge(exact_matches, faiss_matches, bm25_matches, all_chunks_dict)
    reranked = reranker.rerank(queries["semantic_query"], top_candidates)
    policy_id, aggregated, score = agg.aggregate(reranked, all_chunks, norm_claim.insurance.primary.payer, norm_claim.procedure.code, norm_claim.clinical_domain)
    ana_output = analyzer.analyze_chunks(aggregated)
    evidence = eb.build_evidence(policy_id, norm_claim.insurance.primary.payer, ana_output, aggregated)
    prompt = prompt_builder.build_prompt(norm_claim.dict(), evidence)
    final_out = llm.generate_claim_output(norm_claim.claim_id, policy_id, norm_claim.insurance.primary.payer, score, evidence, prompt)
    cleaned = validator.filter_decision_fields(final_out)
    validator.validate(cleaned, policy_id)
    print("Warm-up complete.")
    
    num_runs = 100
    print(f"\nExecuting {num_runs} benchmark runs sequentially...")
    
    for i in range(num_runs):
        t_pipeline_start = time.time()
        
        # 1. Normalization
        t_start = time.time()
        norm_claim = normalize_claim_input(claim_input)
        latencies["normalization"].append((time.time() - t_start) * 1000)
        
        # 2. Query Builder
        t_start = time.time()
        queries = qb.build_query(norm_claim)
        latencies["query_builder"].append((time.time() - t_start) * 1000)
        
        # 3. Exact Matcher
        t_start = time.time()
        exact_matches = em.retrieve(queries["structured"])
        latencies["exact_matching"].append((time.time() - t_start) * 1000)
        
        # 4. BGE Embedder
        t_start = time.time()
        q_vec = embedder.embed_query(queries["semantic_query"])
        latencies["embedding"].append((time.time() - t_start) * 1000)
        
        # 5. FAISS Retrieval
        t_start = time.time()
        faiss_matches = faiss_ret.retrieve(q_vec, top_k=config["candidate_pool_size"])
        latencies["faiss_retrieval"].append((time.time() - t_start) * 1000)
        
        # 6. BM25 Retrieval
        t_start = time.time()
        bm25_matches = bm25_ret.retrieve(queries["bm25_query"], top_k=config["candidate_pool_size"])
        latencies["bm25_retrieval"].append((time.time() - t_start) * 1000)
        
        # 7. Candidate Pool Merging
        t_start = time.time()
        top_candidates = pool.merge(exact_matches, faiss_matches, bm25_matches, all_chunks_dict)
        latencies["merging"].append((time.time() - t_start) * 1000)
        
        # 8. Reranking
        t_start = time.time()
        reranked = reranker.rerank(queries["semantic_query"], top_candidates)
        latencies["reranking"].append((time.time() - t_start) * 1000)
        
        # 9. Policy Aggregation
        t_start = time.time()
        policy_id, aggregated, score = agg.aggregate(reranked, all_chunks, norm_claim.insurance.primary.payer, norm_claim.procedure.code, norm_claim.clinical_domain)
        latencies["aggregation"].append((time.time() - t_start) * 1000)
        
        # 10. Deterministic Analysis
        t_start = time.time()
        ana_output = analyzer.analyze_chunks(aggregated)
        latencies["deterministic_analysis"].append((time.time() - t_start) * 1000)
        
        # 11. Evidence Building
        t_start = time.time()
        evidence = eb.build_evidence(policy_id, norm_claim.insurance.primary.payer, ana_output, aggregated)
        latencies["evidence_building"].append((time.time() - t_start) * 1000)
        
        # 12. LLM Generation
        t_start = time.time()
        prompt = prompt_builder.build_prompt(norm_claim.dict(), evidence)
        final_out = llm.generate_claim_output(norm_claim.claim_id, policy_id, norm_claim.insurance.primary.payer, score, evidence, prompt)
        latencies["llm_generation"].append((time.time() - t_start) * 1000)
        
        # 13. Output Validation
        t_start = time.time()
        cleaned = validator.filter_decision_fields(final_out)
        validator.validate(cleaned, policy_id)
        latencies["validation"].append((time.time() - t_start) * 1000)
        
        # Total latency
        latencies["total_pipeline"].append((time.time() - t_pipeline_start) * 1000)
        
        if (i + 1) % 20 == 0:
            print(f" Completed {i + 1}/{num_runs} runs.")
            
    mem_final = get_memory_usage_mb()
    print(f"\nFinal Memory Usage: {mem_final:.2f} MB")
    
    # Calculate stats
    stats = {}
    for comp, l_list in latencies.items():
        arr = np.array(l_list)
        stats[comp] = {
            "p50": float(np.percentile(arr, 50)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "mean": float(np.mean(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr))
        }
        
    # File Sizes
    file_sizes = {}
    path_mappings = {
        "raw_data": config["paths"]["raw_data"],
        "processed_chunks": config["paths"]["processed_chunks"],
        "embeddings": os.path.join(config["paths"]["embeddings"], "chunk_embeddings.npy"),
        "faiss_index": os.path.join(config["paths"]["vector_store"], "index.faiss"),
        "faiss_mapping": os.path.join(config["paths"]["vector_store"], "mapping.json"),
        "bm25_index": os.path.join(config["paths"]["vector_store"], "bm25.pkl")
    }
    
    for label, path in path_mappings.items():
        if os.path.exists(path):
            file_sizes[label] = {
                "path": path,
                "size_bytes": os.path.getsize(path),
                "size_kb": os.path.getsize(path) / 1024.0,
                "size_mb": os.path.getsize(path) / (1024.0 * 1024.0)
            }
        else:
            file_sizes[label] = {
                "path": path,
                "size_bytes": 0,
                "size_kb": 0.0,
                "size_mb": 0.0
            }
            
    benchmark_json = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware_and_environment": {
            "os": "Windows",
            "initial_memory_mb": mem_start,
            "component_load_time_sec": load_time_sec,
            "peak_memory_mb": mem_final,
            "model_memory_footprint_mb": model_memory_mb
        },
        "file_sizes": file_sizes,
        "component_latencies_ms": stats
    }
    
    # Save JSON report
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", "benchmark_report.json"), "w", encoding="utf-8") as f:
        json.dump(benchmark_json, f, indent=2)
        
    # Write Markdown report
    md_report = f"""# Prior Authorization Retrieval RAG Benchmark Report

Generated: {benchmark_json["timestamp"]}

## Hardware & Environment Overview
* **OS**: Windows
* **Device**: CPU Only (configured in `config.yaml`)
* **Component Load Time**: {load_time_sec:.2f} seconds
* **Initial RAM Usage**: {mem_start:.2f} MB
* **Peak/Final RAM Usage**: {mem_final:.2f} MB
* **Pipeline Memory Footprint**: {model_memory_mb:.2f} MB

## Component & Pipeline Latencies (in milliseconds)
Based on {num_runs} sequential execution runs.

| Component | P50 (Median) | P90 | P95 | P99 | Mean | Min | Max |
|---|---|---|---|---|---|---|---|
| **Normalization** | {stats["normalization"]["p50"]:.2f} | {stats["normalization"]["p90"]:.2f} | {stats["normalization"]["p95"]:.2f} | {stats["normalization"]["p99"]:.2f} | {stats["normalization"]["mean"]:.2f} | {stats["normalization"]["min"]:.2f} | {stats["normalization"]["max"]:.2f} |
| **Query Builder** | {stats["query_builder"]["p50"]:.2f} | {stats["query_builder"]["p90"]:.2f} | {stats["query_builder"]["p95"]:.2f} | {stats["query_builder"]["p99"]:.2f} | {stats["query_builder"]["mean"]:.2f} | {stats["query_builder"]["min"]:.2f} | {stats["query_builder"]["max"]:.2f} |
| **Exact Matching** | {stats["exact_matching"]["p50"]:.2f} | {stats["exact_matching"]["p90"]:.2f} | {stats["exact_matching"]["p95"]:.2f} | {stats["exact_matching"]["p99"]:.2f} | {stats["exact_matching"]["mean"]:.2f} | {stats["exact_matching"]["min"]:.2f} | {stats["exact_matching"]["max"]:.2f} |
| **BGE Query Embedding** | {stats["embedding"]["p50"]:.2f} | {stats["embedding"]["p90"]:.2f} | {stats["embedding"]["p95"]:.2f} | {stats["embedding"]["p99"]:.2f} | {stats["embedding"]["mean"]:.2f} | {stats["embedding"]["min"]:.2f} | {stats["embedding"]["max"]:.2f} |
| **FAISS Vector Search** | {stats["faiss_retrieval"]["p50"]:.2f} | {stats["faiss_retrieval"]["p90"]:.2f} | {stats["faiss_retrieval"]["p95"]:.2f} | {stats["faiss_retrieval"]["p99"]:.2f} | {stats["faiss_retrieval"]["mean"]:.2f} | {stats["faiss_retrieval"]["min"]:.2f} | {stats["faiss_retrieval"]["max"]:.2f} |
| **BM25 Keyword Search** | {stats["bm25_retrieval"]["p50"]:.2f} | {stats["bm25_retrieval"]["p90"]:.2f} | {stats["bm25_retrieval"]["p95"]:.2f} | {stats["bm25_retrieval"]["p99"]:.2f} | {stats["bm25_retrieval"]["mean"]:.2f} | {stats["bm25_retrieval"]["min"]:.2f} | {stats["bm25_retrieval"]["max"]:.2f} |
| **Candidate Merging** | {stats["merging"]["p50"]:.2f} | {stats["merging"]["p90"]:.2f} | {stats["merging"]["p95"]:.2f} | {stats["merging"]["p99"]:.2f} | {stats["merging"]["mean"]:.2f} | {stats["merging"]["min"]:.2f} | {stats["merging"]["max"]:.2f} |
| **BGE Reranking** | {stats["reranking"]["p50"]:.2f} | {stats["reranking"]["p90"]:.2f} | {stats["reranking"]["p95"]:.2f} | {stats["reranking"]["p99"]:.2f} | {stats["reranking"]["mean"]:.2f} | {stats["reranking"]["min"]:.2f} | {stats["reranking"]["max"]:.2f} |
| **Policy Aggregation** | {stats["aggregation"]["p50"]:.2f} | {stats["aggregation"]["p90"]:.2f} | {stats["aggregation"]["p95"]:.2f} | {stats["aggregation"]["p99"]:.2f} | {stats["aggregation"]["mean"]:.2f} | {stats["aggregation"]["min"]:.2f} | {stats["aggregation"]["max"]:.2f} |
| **Deterministic Analysis** | {stats["deterministic_analysis"]["p50"]:.2f} | {stats["deterministic_analysis"]["p90"]:.2f} | {stats["deterministic_analysis"]["p95"]:.2f} | {stats["deterministic_analysis"]["p99"]:.2f} | {stats["deterministic_analysis"]["mean"]:.2f} | {stats["deterministic_analysis"]["min"]:.2f} | {stats["deterministic_analysis"]["max"]:.2f} |
| **Evidence Building** | {stats["evidence_building"]["p50"]:.2f} | {stats["evidence_building"]["p90"]:.2f} | {stats["evidence_building"]["p95"]:.2f} | {stats["evidence_building"]["p99"]:.2f} | {stats["evidence_building"]["mean"]:.2f} | {stats["evidence_building"]["min"]:.2f} | {stats["evidence_building"]["max"]:.2f} |
| **LLM Output Gen / Fallback** | {stats["llm_generation"]["p50"]:.2f} | {stats["llm_generation"]["p90"]:.2f} | {stats["llm_generation"]["p95"]:.2f} | {stats["llm_generation"]["p99"]:.2f} | {stats["llm_generation"]["mean"]:.2f} | {stats["llm_generation"]["min"]:.2f} | {stats["llm_generation"]["max"]:.2f} |
| **Output Validation** | {stats["validation"]["p50"]:.2f} | {stats["validation"]["p90"]:.2f} | {stats["validation"]["p95"]:.2f} | {stats["validation"]["p99"]:.2f} | {stats["validation"]["mean"]:.2f} | {stats["validation"]["min"]:.2f} | {stats["validation"]["max"]:.2f} |
| **TOTAL PIPELINE LATENCY** | **{stats["total_pipeline"]["p50"]:.2f}** | **{stats["total_pipeline"]["p90"]:.2f}** | **{stats["total_pipeline"]["p95"]:.2f}** | **{stats["total_pipeline"]["p99"]:.2f}** | **{stats["total_pipeline"]["mean"]:.2f}** | **{stats["total_pipeline"]["min"]:.2f}** | **{stats["total_pipeline"]["max"]:.2f}** |

## Index & Data Storage footprint

| Index Component | File Path | Size (KB) | Size (MB) |
|---|---|---|---|
| **Raw Data** | `{file_sizes["raw_data"]["path"]}` | {file_sizes["raw_data"]["size_kb"]:.2f} | {file_sizes["raw_data"]["size_mb"]:.4f} |
| **Processed Chunks** | `{file_sizes["processed_chunks"]["path"]}` | {file_sizes["processed_chunks"]["size_kb"]:.2f} | {file_sizes["processed_chunks"]["size_mb"]:.4f} |
| **BGE Embeddings npy** | `{file_sizes["embeddings"]["path"]}` | {file_sizes["embeddings"]["size_kb"]:.2f} | {file_sizes["embeddings"]["size_mb"]:.4f} |
| **FAISS Index** | `{file_sizes["faiss_index"]["path"]}` | {file_sizes["faiss_index"]["size_kb"]:.2f} | {file_sizes["faiss_index"]["size_mb"]:.4f} |
| **FAISS Mapping metadata** | `{file_sizes["faiss_mapping"]["path"]}` | {file_sizes["faiss_mapping"]["size_kb"]:.2f} | {file_sizes["faiss_mapping"]["size_mb"]:.4f} |
| **BM25 PKL Index** | `{file_sizes["bm25_index"]["path"]}` | {file_sizes["bm25_index"]["size_kb"]:.2f} | {file_sizes["bm25_index"]["size_mb"]:.4f} |

"""
    with open(os.path.join("reports", "benchmark_report.md"), "w", encoding="utf-8") as f:
        f.write(md_report)
        
    print("\nBenchmark completed successfully. Reports generated under reports/benchmark_report.json and reports/benchmark_report.md.")

if __name__ == "__main__":
    main()
