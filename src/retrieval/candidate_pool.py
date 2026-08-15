from typing import List, Dict, Any

class CandidatePool:
    def __init__(self, exact_weight: float = 0.5, bge_weight: float = 0.3, bm25_weight: float = 0.2):
        self.exact_weight = exact_weight
        self.bge_weight = bge_weight
        self.bm25_weight = bm25_weight
        
    def merge(
        self,
        exact_results: List[Dict[str, Any]],
        faiss_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        all_chunks_dict: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge results from Exact matching, FAISS (BGE), and BM25, deduplicating and calculating candidate scores.
        Returns Top 10 candidate chunks.
        """
        candidates: Dict[str, Dict[str, Any]] = {}
        
        # Helper to register or update candidates
        def add_score(chunk_id: str, score: float, source: str):
            if chunk_id not in all_chunks_dict:
                return
            if chunk_id not in candidates:
                candidates[chunk_id] = {
                    "chunk": all_chunks_dict[chunk_id],
                    "chunk_id": chunk_id,
                    "policy_id": all_chunks_dict[chunk_id]["policy_id"],
                    "exact_score": 0.0,
                    "bge_score": 0.0,
                    "bm25_score": 0.0,
                    "sources": []
                }
            candidates[chunk_id]["sources"].append(source)
            if source == "exact":
                candidates[chunk_id]["exact_score"] = score
            elif source == "faiss":
                candidates[chunk_id]["bge_score"] = score
            elif source == "bm25":
                candidates[chunk_id]["bm25_score"] = score

        # Add all sources
        for res in exact_results:
            add_score(res["chunk"]["chunk_id"], res["score"], "exact")
            
        for res in faiss_results:
            add_score(res["chunk_id"], res["score"], "faiss")
            
        for res in bm25_results:
            add_score(res["chunk_id"], res["score"], "bm25")
            
        # Compute final merged scores
        pool_list = []
        for chunk_id, item in candidates.items():
            combined_score = (
                self.exact_weight * item["exact_score"] +
                self.bge_weight * item["bge_score"] +
                self.bm25_weight * item["bm25_score"]
            )
            item["combined_score"] = combined_score
            pool_list.append(item)
            
        # Sort by combined score descending
        pool_list.sort(key=lambda x: x["combined_score"], reverse=True)
        
        # Return Top 10 candidates
        return pool_list[:10]
