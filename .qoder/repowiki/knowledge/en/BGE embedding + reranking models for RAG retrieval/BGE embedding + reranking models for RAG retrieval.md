---
kind: external_dependency
name: BGE embedding + reranking models for RAG retrieval
slug: bge-embeddings-reranker
category: external_dependency
category_hints:
    - framework_behavior
    - client_constraint
scope:
    - '**'
source_files:
    - config/config.yaml
    - .env.example
    - rag/embeddings/bge_embedder.py
---

### Identity & Role
- The RAG pipeline uses Hugging Face sentence-transformers with the BAAI BGE family: `BAAI/bge-base-en-v1.5` for embeddings and `BAAI/bge-reranker-base` for candidate reranking. Models are cached under `HF_HOME` / `TRANSFORMERS_CACHE` / `TORCH_HOME` (configured via `.env.example`).

### Integration Point
- `config/config.yaml` declares both model names plus `candidate_pool_size: 10` and `final_policy_chunk_count: 3`.
- `rag/embeddings/bge_embedder.py` (created during this session) wraps `SentenceTransformer` to embed queries into FAISS vectors stored under `data/vector_store/index.faiss`.
- `rag/reranking/bge_reranker.py` applies cross-encoder reranking before aggregation.

### Client Constraint
- Default device is `cpu` per config; large model downloads go to `E:\RAG\cache` on the development machine. The embedding module was missing from source and had to be recreated to match the repo's lazy-load pattern used elsewhere.