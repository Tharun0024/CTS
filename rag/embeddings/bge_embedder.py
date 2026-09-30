import os
import numpy as np
import torch
from typing import List, Union
from transformers import AutoModel, AutoTokenizer


# BGE models recommend an instruction prefix for retrieval queries
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class BGEEmbedder:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BGEEmbedder, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5", device: str = "cpu", cache_dir: str = ".cache/hf"):
        if getattr(self, "_initialized", False):
            return
        # Store config — model loads lazily on first embed call
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
        print(f"Loading embedding model '{self.model_name}' (this may take a moment)...")
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
            self.model = AutoModel.from_config(config)
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
        self.model.to(self.device)
        self.model.eval()

        # Freeze parameters — inference only, no training
        for param in self.model.parameters():
            param.requires_grad = False

        print(f"Embedding model loaded successfully.")

    @staticmethod
    def _stream_state_dict(safetensors_path: str) -> dict:
        """Read safetensors tensor-by-tensor into RAM (no memory mapping)."""
        from safetensors import safe_open

        state_dict = {}
        with safe_open(safetensors_path, framework="pt", device="cpu") as f:
            for key in f.keys():
                state_dict[key] = f.get_tensor(key)
        return state_dict

    def _encode(self, texts: List[str], add_query_instruction: bool = False) -> np.ndarray:
        """Encode texts into L2-normalized CLS-pooled embeddings."""
        self._load_model()

        if add_query_instruction:
            texts = [QUERY_INSTRUCTION + t for t in texts]

        with torch.no_grad():
            inputs = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512
            ).to(self.device)
            outputs = self.model(**inputs)
            # CLS pooling
            embeddings = outputs.last_hidden_state[:, 0]
            # L2 normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().numpy().astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single search query. Returns a normalized vector of shape (dim,)."""
        vec = self._encode([query], add_query_instruction=True)
        return vec[0]

    def embed_texts(self, texts: Union[str, List[str]], is_query: bool = False) -> np.ndarray:
        """Embed a batch of texts. Returns a normalized array of shape (N, dim)."""
        if isinstance(texts, str):
            texts = [texts]
        return self._encode(list(texts), add_query_instruction=is_query)

    @staticmethod
    def save_embeddings(embeddings: np.ndarray, file_path: str) -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        np.save(file_path, np.asarray(embeddings, dtype=np.float32))
