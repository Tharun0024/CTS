import os
import json
import yaml
import numpy as np
from src.normalization.policy_normalizer import normalize_policies_dataset
from src.chunking.policy_chunker import chunk_policies
from src.embeddings.bge_embedder import BGEEmbedder
from src.retrieval.faiss_retriever import FAISSRetriever
from src.retrieval.bm25_retriever import BM25Retriever

def main():
    # Load configuration
    config_path = os.path.join("config", "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    raw_data_path = config["paths"]["raw_data"]
    normalized_data_path = config["paths"]["normalized_data"]
    processed_chunks_path = config["paths"]["processed_chunks"]
    
    print("--- STEP 1: Policy Normalization ---")
    normalize_policies_dataset(raw_data_path, normalized_data_path)
    
    print("\n--- STEP 2: Policy Chunking ---")
    chunk_policies(normalized_data_path, processed_chunks_path)
    
    # Load chunk records
    with open(processed_chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    print(f"\n--- STEP 3: BGE Embedding generation for {len(chunks)} chunks ---")
    # Formulate index strings for each chunk
    texts_to_embed = []
    for chunk in chunks:
        payer = chunk.get("payer", "")
        policy_id = chunk.get("policy_id", "")
        title = chunk.get("policy_title", "")
        domain = chunk.get("clinical_domain", "")
        section = chunk.get("section", "")
        crit_name = chunk.get("criterion_name", "")
        text = chunk.get("text", "")
        
        # Format chunk representation
        repr_text = (
            f"payer: {payer} | policy: {policy_id} - {title} | clinical domain: {domain} | "
            f"section: {section} | criterion: {crit_name} | criteria details: {text}"
        )
        texts_to_embed.append(repr_text)
        
    # Initialize embedder
    embedder = BGEEmbedder(
        model_name=config["embedding_model"],
        device=config["device"],
        cache_dir=config["paths"]["cache"]
    )
    
    # Compute embeddings
    embeddings = embedder.embed_texts(texts_to_embed)
    
    # Save embeddings
    embeddings_file = os.path.join(config["paths"]["embeddings"], "chunk_embeddings.npy")
    embedder.save_embeddings(embeddings, embeddings_file)
    print(f"Computed and saved embeddings to {embeddings_file}. Shape: {embeddings.shape}")
    
    print("\n--- STEP 4: FAISS Index Construction ---")
    # Build FAISS index
    retriever = FAISSRetriever(
        index_dir=config["paths"]["vector_store"],
        dimension=embeddings.shape[1]
    )
    
    # Pack metadata mapping
    metadata = []
    for chunk in chunks:
        metadata.append({
            "chunk_id": chunk["chunk_id"],
            "policy_id": chunk["policy_id"]
        })
        
    retriever.build_index(embeddings, metadata)
    retriever.save()
    
    print("\n--- STEP 5: BM25 Index Construction ---")
    bm25_retriever = BM25Retriever(
        index_path=os.path.join(config["paths"]["vector_store"], "bm25.pkl")
    )
    bm25_retriever.build_index(chunks)
    bm25_retriever.save()
    
    print("\n===========================================")
    print("ALL INDEXING PIPELINES SUCCESSFULLY BUILT.")
    print("===========================================")

if __name__ == "__main__":
    main()
