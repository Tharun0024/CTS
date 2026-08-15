import os
import json
import faiss
import numpy as np
from typing import List, Dict, Any, Tuple

class FAISSRetriever:
    def __init__(self, index_dir: str = "E:/RAG/vector_store", dimension: int = 768):
        self.index_dir = index_dir
        self.dimension = dimension
        self.index = None
        self.vector_to_chunk_map: List[Dict[str, str]] = [] # Maps index offset to {chunk_id, policy_id}

    def build_index(self, embeddings: np.ndarray, chunk_metadata: List[Dict[str, str]]):
        """
        Build the FAISS index from document embeddings and associate each vector with metadata.
        """
        # BGE base uses 768 dimensions
        assert embeddings.shape[1] == self.dimension, f"Expected dimension {self.dimension}, got {embeddings.shape[1]}"
        
        # Use IndexFlatIP (Inner Product) since embeddings are normalized (Cosine similarity)
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # Add to index
        self.index.add(embeddings.astype("float32"))
        
        # Store metadata mapping
        self.vector_to_chunk_map = []
        for meta in chunk_metadata:
            self.vector_to_chunk_map.append({
                "chunk_id": meta["chunk_id"],
                "policy_id": meta["policy_id"]
            })
            
    def save(self):
        """
        Save FAISS index and mapping file to disk.
        """
        os.makedirs(self.index_dir, exist_ok=True)
        index_path = os.path.join(self.index_dir, "index.faiss")
        mapping_path = os.path.join(self.index_dir, "mapping.json")
        
        # Save FAISS index
        faiss.write_index(self.index, index_path)
        
        # Save mapping
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump(self.vector_to_chunk_map, f, indent=2)
            
        print(f"FAISS index and metadata map successfully saved to {self.index_dir}")

    def load(self):
        """
        Load FAISS index and mapping file from disk.
        """
        index_path = os.path.join(self.index_dir, "index.faiss")
        mapping_path = os.path.join(self.index_dir, "mapping.json")
        
        if not os.path.exists(index_path) or not os.path.exists(mapping_path):
            raise FileNotFoundError(f"FAISS index files not found in {self.index_dir}")
            
        self.index = faiss.read_index(index_path)
        
        with open(mapping_path, "r", encoding="utf-8") as f:
            self.vector_to_chunk_map = json.load(f)
            
        print(f"FAISS index and metadata map successfully loaded from {self.index_dir}. Size: {self.index.ntotal} vectors.")

    def retrieve(self, query_vector: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Query FAISS index for the top K closest vectors.
        """
        if self.index is None:
            raise ValueError("FAISS index has not been loaded or built.")
            
        # Reshape to 2D if 1D
        if len(query_vector.shape) == 1:
            query_vector = np.expand_dims(query_vector, axis=0)
            
        # Search index
        scores, indices = self.index.search(query_vector.astype("float32"), top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.vector_to_chunk_map):
                continue
            meta = self.vector_to_chunk_map[idx]
            results.append({
                "chunk_id": meta["chunk_id"],
                "policy_id": meta["policy_id"],
                "score": float(score) # Cosine similarity score
            })
            
        return results
