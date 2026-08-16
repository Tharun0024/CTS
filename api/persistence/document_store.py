"""Document storage interface + local implementation (Phase 7).

The upload path extracts text into evidence (``document_ingest.py``); this
module persists the RAW uploaded bytes so originals are never lost.

LOCAL (default):   ``LocalFileDocumentStore`` writes files under a local
                   directory (``data/documents`` or ``CTS_DOCUMENT_DIR``).
CLOUD replacement: implement ``DocumentStore`` against cloud object storage
                   and inject it into ``SimulationManager(document_store=...)``
                   in ``api/main.py``. Nothing else changes — extraction,
                   evidence shape, provenance and the V1 workflow are
                   storage-agnostic.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional


class DocumentStore(ABC):
    """Stores raw uploaded document bytes; returns a stable reference string."""

    @abstractmethod
    def save(self, document_id: str, filename: str, content: bytes) -> str:
        """Persist ``content`` and return the storage reference."""

    @abstractmethod
    def load(self, reference: str) -> Optional[bytes]:
        """Return the stored bytes for ``reference`` or None when absent."""


class LocalFileDocumentStore(DocumentStore):
    """Filesystem-backed store: one file per document under ``root``."""

    def __init__(self, root: Optional[str] = None):
        self.root = root or os.getenv(
            "CTS_DOCUMENT_DIR", os.path.join("data", "documents")
        )

    def _path_for(self, reference: str) -> str:
        return os.path.join(self.root, os.path.basename(reference))

    def save(self, document_id: str, filename: str, content: bytes) -> str:
        os.makedirs(self.root, exist_ok=True)
        safe_name = "".join(
            ch if (ch.isalnum() or ch in "._-") else "_" for ch in (filename or "upload")
        )
        reference = f"{document_id}_{safe_name}"
        with open(self._path_for(reference), "wb") as handle:
            handle.write(content)
        return f"LOCAL:{reference}"

    def load(self, reference: str) -> Optional[bytes]:
        if not reference or not reference.startswith("LOCAL:"):
            return None
        path = self._path_for(reference[len("LOCAL:"):])
        if not os.path.exists(path):
            return None
        with open(path, "rb") as handle:
            return handle.read()
