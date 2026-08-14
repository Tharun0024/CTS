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

    def __init__(self, model_name: str = "BAAI/bge-reranker-base", device: str = "cpu", cache_dir: str = "E:/RAG/cache"):
        if getattr(self, "_initialized", False):
            return
        # Store config — model loads lazily on first rerank() call
        os.environ["HF_HOME"] = cache_dir
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir
        self.tokenizer = None
        self.model = None
        self._initialized = True

    def _load_model(self):
        """Lazily load tokenizer and model on first use."""
        if self.model is not None:
            return
        print(f"Loading reranker model '{self.model_name}' (this may take a moment)...")
        cache_models_dir = os.path.join(self.cache_dir, "models")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            cache_dir=cache_models_dir
        )

        # Load model weights directly into CPU memory without memory-mapping
        # (avoids Windows pagefile exhaustion / OS error 1455)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            cache_dir=cache_models_dir,
            low_cpu_mem_usage=True,
        )
        self.model.to(self.device)
        self.model.eval()

        # Freeze parameters — inference only, no training
        for param in self.model.parameters():
            param.requires_grad = False

        print(f"Reranker model loaded successfully.")

    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank a list of candidates against the search query.
        Updates each candidate with a 'rerank_score' and returns the sorted list.
        """
        if not candidates:
            return []

        # Load model on first call
        self._load_model()

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
