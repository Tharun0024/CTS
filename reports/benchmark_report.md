# Prior Authorization Retrieval RAG Benchmark Report

Generated: 2026-08-14 15:05:59

## Hardware & Environment Overview
* **OS**: Windows
* **Device**: CPU Only (configured in `config.yaml`)
* **Component Load Time**: 8.90 seconds
* **Initial RAM Usage**: 621.34 MB
* **Peak/Final RAM Usage**: 1737.90 MB
* **Pipeline Memory Footprint**: 269.43 MB

## Component & Pipeline Latencies (in milliseconds)
Based on 100 sequential execution runs.

| Component | P50 (Median) | P90 | P95 | P99 | Mean | Min | Max |
|---|---|---|---|---|---|---|---|
| **Normalization** | 0.03 | 0.08 | 0.13 | 0.52 | 0.06 | 0.02 | 1.01 |
| **Query Builder** | 0.02 | 0.02 | 0.04 | 0.08 | 0.02 | 0.01 | 0.21 |
| **Exact Matching** | 0.23 | 0.39 | 0.44 | 0.74 | 0.27 | 0.16 | 1.08 |
| **BGE Query Embedding** | 191.32 | 301.78 | 347.44 | 417.84 | 214.36 | 140.12 | 720.62 |
| **FAISS Vector Search** | 0.13 | 0.24 | 0.47 | 9.32 | 0.45 | 0.09 | 13.40 |
| **BM25 Keyword Search** | 0.48 | 0.75 | 1.37 | 6.46 | 0.84 | 0.37 | 20.03 |
| **Candidate Merging** | 0.06 | 0.10 | 0.12 | 0.19 | 0.07 | 0.05 | 0.45 |
| **BGE Reranking** | 15763.79 | 18855.62 | 20181.32 | 21992.15 | 16151.48 | 13659.64 | 22153.39 |
| **Policy Aggregation** | 0.10 | 0.15 | 0.18 | 0.51 | 0.12 | 0.07 | 0.93 |
| **Deterministic Analysis** | 0.03 | 0.05 | 0.06 | 0.20 | 0.04 | 0.02 | 0.24 |
| **Evidence Building** | 0.01 | 0.02 | 0.02 | 0.07 | 0.01 | 0.01 | 0.10 |
| **LLM Output Gen / Fallback** | 0.16 | 0.32 | 0.48 | 1.61 | 0.23 | 0.10 | 2.04 |
| **Output Validation** | 0.08 | 0.13 | 0.33 | 0.96 | 0.13 | 0.05 | 2.24 |
| **TOTAL PIPELINE LATENCY** | **15979.20** | **19120.75** | **20425.71** | **22209.87** | **16368.13** | **13853.30** | **22365.00** |

## Index & Data Storage footprint

| Index Component | File Path | Size (KB) | Size (MB) |
|---|---|---|---|
| **Raw Data** | `E:/RAG/data/raw/ragdata.jsonl` | 29.96 | 0.0293 |
| **Processed Chunks** | `E:/RAG/data/processed/chunks.json` | 36.30 | 0.0355 |
| **BGE Embeddings npy** | `E:/RAG/embeddings\chunk_embeddings.npy` | 72.12 | 0.0704 |
| **FAISS Index** | `E:/RAG/vector_store\index.faiss` | 72.04 | 0.0704 |
| **FAISS Mapping metadata** | `E:/RAG/vector_store\mapping.json` | 1.89 | 0.0018 |
| **BM25 PKL Index** | `E:/RAG/vector_store\bm25.pkl` | 21.31 | 0.0208 |

