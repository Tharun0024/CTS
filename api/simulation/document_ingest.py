"""Document ingestion: extraction + provenance-carrying evidence (Phase 5B).

upload -> extract contents -> provider-side evidence/document -> patient_id

Extraction is deterministic and dependency-free:
  - text payloads decode as UTF-8;
  - PDF payloads have their visible text pulled from ``(text) Tj/TJ`` content
    stream operators (enough for structured clinical uploads);
  - anything else falls back to printable ASCII runs.

The produced evidence item uses the canonical V1 evidence shape and carries
full provenance (``DOC:{document_id}:{filename}``) so downstream decisions
can always trace the fact back to the uploaded document. No content is
invented: when extraction yields nothing, the evidence text says so and the
item fails closed downstream like any unsupported record.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

_PDF_TEXT_SHOW_RE = re.compile(rb"\(((?:\\.|[^()\\])*)\)\s*T[jJ]")
_PRINTABLE_RUN_RE = re.compile(rb"[\x20-\x7E\n\r\t]{4,}")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unescape_pdf_string(raw: bytes) -> str:
    text = raw.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
    return text.replace(b"\\n", b"\n").decode("latin-1", errors="replace")


def extract_document_text(filename: str, content: bytes) -> Tuple[str, str]:
    """Extract readable text from an uploaded document.

    Returns ``(text, extraction_mode)`` where mode is one of
    ``text`` / ``pdf`` / ``binary-scan`` / ``empty``.
    """
    if not content:
        return "", "empty"

    name = (filename or "").lower()
    if name.endswith(".pdf") or content[:5] == b"%PDF-":
        fragments = [_unescape_pdf_string(m.group(1)) for m in _PDF_TEXT_SHOW_RE.finditer(content)]
        text = "\n".join(fragment for fragment in fragments if fragment.strip())
        if text.strip():
            return text.strip(), "pdf"
    else:
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError:
            decoded = None
        # Require VISIBLE content: control-byte-only payloads are not text.
        if decoded is not None and decoded.strip() and re.search(r"[\w\d]", decoded):
            return decoded.strip(), "text"

    runs = [run.decode("ascii") for run in _PRINTABLE_RUN_RE.findall(content)]
    text = "\n".join(run for run in runs if run.strip())
    if text.strip():
        return text.strip(), "binary-scan"
    return "", "empty"


def build_document_evidence(
    document_id: str,
    filename: str,
    patient_id: str,
    extracted_text: str,
    extraction_mode: str,
    evidence_key: Optional[str] = None,
    doc_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the canonical V1 evidence item for an uploaded document.

    Provenance is always ``DOC:{document_id}:{filename}``; the extracted text
    (truncated) and upload metadata travel inside ``extracted_facts`` so the
    pipeline evaluates only what was actually in the document.

    The evidence_key stays UNIQUE per document (the document's own key) so an
    upload never collapses into the same evidence group as an existing record
    (key collapse would flag a false conflict and force HUMAN_REVIEW). When
    the caller associates the document with a semantic criterion key, it is
    carried in ``extracted_facts["requested_evidence_key"]`` for traceability.
    """
    provenance = f"DOC:{document_id}:{filename}"
    snippet = (extracted_text or "")[:1000]
    uploaded_at = _utc_now_iso()
    extracted_facts: Dict[str, Any] = {
        "document_id": document_id,
        "filename": filename,
        "patient_id": patient_id,
        "doc_type": doc_type or "uploaded_document",
        "extraction_mode": extraction_mode,
        "extracted_text": snippet,
        "content_reference": snippet or "No extractable text found in uploaded document.",
        "uploaded_at": uploaded_at,
        "sensitivity": "ROUTINE",
        "provenance": provenance,
    }
    if evidence_key:
        extracted_facts["requested_evidence_key"] = evidence_key
    return {
        "evidence_key": f"document_{document_id.lower()}",
        "evidence_id": f"{document_id}-EV1",
        "source": "Uploaded Document",
        "status": "verified",
        "confidence_score": 0.96,
        "is_ambiguous": False,
        "extracted_facts": extracted_facts,
        "unstructured_text": snippet or None,
    }
