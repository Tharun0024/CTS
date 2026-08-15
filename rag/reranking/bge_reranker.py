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

    def __init__(self, model_name: str = "BAAI/bge-reranker-base", device: str = "cpu", cache_dir: str = ".cache/hf"):
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

        # Stream safetensors tensors directly into RAM without memory-mapping.
        # On Windows the memory-mapped load path exhausts the paging file
        # (os error 1455) or faults with an access violation inside
        # torch.storage under load; meta-init + assign streams the weights in
        # a single allocation, avoiding both failure modes.
        from transformers import AutoConfig
        from huggingface_hub import hf_hub_download

        config = AutoConfig.from_pretrained(self.model_name, cache_dir=cache_models_dir)
        try:
            repo_path = hf_hub_download(
                self.model_name, "model.safetensors",
                cache_dir=cache_models_dir, local_files_only=True,
            )
        except Exception:
            repo_path = hf_hub_download(
                self.model_name, "model.safetensors", cache_dir=cache_models_dir
            )

        import gc
        gc.collect()
        with torch.device("meta"):
            self.model = AutoModelForSequenceClassification.from_config(config)
        state_dict = self._stream_state_dict(repo_path)
        self.model.load_state_dict(state_dict, assign=True, strict=False)
        del state_dict
        gc.collect()
        # Non-persistent buffers (position_ids/token_type_ids) are not stored
        # in the shard and remain on meta; materialize them with their init
        # values so .to(device) and forward work.
        for module in self.model.modules():
            for buf_name, buf in list(module.named_buffers(recurse=False)):
                if buf is not None and buf.device.type == "meta":
                    setattr(module, buf_name, torch.zeros(buf.shape, dtype=buf.dtype))
        self.model.tie_weights()
        self.model.to(self.device)
        self.model.eval()

        # Freeze parameters — inference only, no training
        for param in self.model.parameters():
            param.requires_grad = False

        print(f"Reranker model loaded successfully.")

    @staticmethod
    def _stream_state_dict(safetensors_path: str) -> dict:
        """Read safetensors tensor-by-tensor into RAM (no memory mapping)."""
        from safetensors import safe_open

        state_dict = {}
        with safe_open(safetensors_path, framework="pt", device="cpu") as f:
            for key in f.keys():
                state_dict[key] = f.get_tensor(key)
        return state_dict

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
