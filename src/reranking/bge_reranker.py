import os
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from typing import List, Dict, Any

class BGEReranker:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BGEReranker, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str = "cpu", cache_dir: str = "E:/RAG/cache"):
        if getattr(self, "_initialized", False):
            return
        # Configure cache environments
        os.environ["HF_HOME"] = cache_dir
        
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=os.path.join(cache_dir, "models")
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            cache_dir=os.path.join(cache_dir, "models")
        )
        self.model.to(self.device)
        self.model.eval()
        
        # Freeze reranker parameters
        for param in self.model.parameters():
            param.requires_grad = False
        self._initialized = True
            
    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank a list of candidates against the search query.
        Updates each candidate with a 'rerank_score' and returns the sorted list.
        """
        if not candidates:
            return []
            
        chunk_texts = []
        for c in candidates:
            chunk = c["chunk"]
            payer = chunk.get("payer", "")
            policy_id = chunk.get("policy_id", "")
            title = chunk.get("policy_title", "")
            domain = chunk.get("clinical_domain", "")
            section = chunk.get("section", "")
            crit_name = chunk.get("criterion_name", "")
            text = chunk.get("text", "")
            
            repr_text = (
                f"payer: {payer} | policy: {policy_id} - {title} | clinical domain: {domain} | "
                f"section: {section} | criterion: {crit_name} | criteria details: {text}"
            )
            chunk_texts.append(repr_text)
            
        pairs = [[query, text] for text in chunk_texts]
        
        with torch.no_grad():
            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512
            ).to(self.device)
            
            # Predict logits
            outputs = self.model(**inputs)
            logits = outputs.logits.view(-1).float()
            
            # Map logit scores to a probability range using sigmoid
            scores = torch.sigmoid(logits).cpu().numpy().tolist()
            
        # Update candidate scores
        for cand, score in zip(candidates, scores):
            cand["rerank_score"] = float(score)
            
        # Sort by rerank score descending
        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return candidates
