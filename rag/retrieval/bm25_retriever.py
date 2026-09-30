import os
import pickle
import re
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

def tokenize(text: str) -> List[str]:
    """
    Lowercase and tokenize text into words.
    """
    clean_text = re.sub(r"[^\w\s-]", " ", text.lower())
    return [word for word in clean_text.split() if word.strip()]

class BM25Retriever:
    def __init__(self, index_path: str = "data/vector_store/bm25.pkl"):
        self.index_path = index_path
        self.bm25 = None
        self.chunks_map: List[Dict[str, str]] = [] # Index to {chunk_id, policy_id}
        
    def build_index(self, chunks: List[Dict[str, Any]]):
        """
        Tokenize key fields in chunks and fit a BM25 model.
        """
        corpus_tokens = []
        self.chunks_map = []
        
        for chunk in chunks:
            text = chunk.get("text", "")
            proc_desc = " ".join(chunk.get("procedure_codes", []))
            diag_desc = " ".join(chunk.get("diagnosis_codes", []))
            crit_name = chunk.get("criterion_name", "")
            section = chunk.get("section", "")
            payer = chunk.get("payer", "")
            
            # Formulate indexing text: heavy keyword content
            indexed_text = f"{payer} {section} {crit_name} {proc_desc} {diag_desc} {text}"
            corpus_tokens.append(tokenize(indexed_text))
            
            self.chunks_map.append({
                "chunk_id": chunk["chunk_id"],
                "policy_id": chunk["policy_id"]
            })
            
        self.bm25 = BM25Okapi(corpus_tokens)
        
    def save(self):
        """
        Save BM25 model and chunk mappings to a pickle file.
        """
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        data = {
            "bm25": self.bm25,
            "chunks_map": self.chunks_map
        }
        with open(self.index_path, "wb") as f:
            pickle.dump(data, f)
        print(f"BM25 index successfully saved to {self.index_path}")
        
    def load(self):
        """
        Load BM25 model and mappings from pickle.
        """
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"BM25 index not found at {self.index_path}")
            
        with open(self.index_path, "rb") as f:
            data = pickle.load(f)
            
        self.bm25 = data["bm25"]
        self.chunks_map = data["chunks_map"]
        print(f"BM25 index successfully loaded from {self.index_path}. Corpus size: {len(self.chunks_map)}")
        
    def retrieve(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve chunks matching query text using BM25.
        Scores are normalized between 0.0 and 1.0 based on the maximum score in the results.
        """
        if self.bm25 is None:
            raise ValueError("BM25 index has not been loaded or built.")
            
        query_tokens = tokenize(query_text)
        if not query_tokens:
            return []
            
        raw_scores = self.bm25.get_scores(query_tokens)
        
        # Zip with index offset
        scored_indices = list(enumerate(raw_scores))
        scored_indices.sort(key=lambda x: x[1], reverse=True)
        
        top_matches = scored_indices[:top_k]
        
        # Calculate max score to normalize
        max_score = max(raw_scores) if len(raw_scores) > 0 else 0.0
        
        results = []
        for idx, score in top_matches:
            if score <= 0:
                continue
            meta = self.chunks_map[idx]
            
            # Normalize
            normalized_score = float(score / max_score) if max_score > 0 else 0.0
            
            results.append({
                "chunk_id": meta["chunk_id"],
                "policy_id": meta["policy_id"],
                "score": normalized_score
            })
            
        return results
