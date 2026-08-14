from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping


def _coerce_to_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _record_evidence_item(key: str, value: Any, source: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    facts = value.get("extracted_facts") or value.get("facts") or {}
    evidence_item = {
        "evidence_key": key,
        "evidence_id": value.get("evidence_id") or value.get("document_id") or f"{key}_id",
        "source": value.get("source") or source,
        "status": value.get("status") or "verified",
        "confidence_score": value.get("confidence_score") or value.get("confidence") or 1.0,
        "is_ambiguous": bool(value.get("is_ambiguous", False)),
        "extracted_facts": facts if isinstance(facts, dict) else {},
        "unstructured_text": value.get("unstructured_text") or value.get("content") or value.get("text"),
    }
    return evidence_item


def _extract_runtime_evidence(runtime_claim: Mapping[str, Any]) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    for section_name, source_name in (
        ("clinical_information", "Clinical Information"),
        ("treatment_history", "Treatment History"),
        ("diagnostic_information", "Diagnostic Information"),
    ):
        section = runtime_claim.get(section_name)
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            evidence_item = _record_evidence_item(key, value, source_name)
            if evidence_item:
                evidence.append(evidence_item)

    for doc_index, doc in enumerate(runtime_claim.get("documents") or []):
        if not isinstance(doc, dict):
            continue
        key = doc.get("evidence_key") or doc.get("document_type") or f"doc_{doc_index}"
        evidence_item = _record_evidence_item(key, doc, "Document Upload")
        if evidence_item:
            evidence.append(evidence_item)

    if isinstance(runtime_claim.get("evidence"), list):
        evidence = deepcopy(runtime_claim["evidence"])

    return evidence


def _extract_runtime_metrics(runtime_claim: Mapping[str, Any]) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    for section_name in ("clinical_information", "treatment_history", "diagnostic_information"):
        section = runtime_claim.get(section_name)
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            if not isinstance(value, dict):
                continue
            facts = value.get("extracted_facts") or value.get("facts") or {}
            if isinstance(facts, dict):
                metrics.update(facts)
            else:
                metrics[key] = value

    patient = runtime_claim.get("patient") or {}
    if isinstance(patient, dict):
        age = patient.get("age")
        if age is not None:
            metrics["patient_age"] = age
        gender = patient.get("gender")
        if gender is not None:
            metrics["patient_gender"] = gender

    if isinstance(runtime_claim.get("clinical_metrics"), dict):
        metrics.update(runtime_claim["clinical_metrics"])

    return metrics


def build_canonical_claim(runtime_claim: Mapping[str, Any]) -> Dict[str, Any]:
    """Convert Version-1 runtime claim data into the current Agent-1 canonical claim contract."""
    if runtime_claim is None:
        raise ValueError("runtime_claim cannot be None")

    if "case_data" in runtime_claim and "evidence" in runtime_claim:
        return deepcopy(dict(runtime_claim))

    patient = runtime_claim.get("patient") or {}
    if not isinstance(patient, dict):
        patient = {}

    claim_id = runtime_claim.get("claim_id") or runtime_claim.get("case_id") or "UNKNOWN-CLAIM"
    age = patient.get("age")
    if age is None:
        age = runtime_claim.get("patient_age", 0)

    diagnoses = _coerce_to_list(runtime_claim.get("diagnoses"))
    procedures = _coerce_to_list(runtime_claim.get("procedures"))

    proc = runtime_claim.get("procedure")
    if isinstance(proc, dict):
        code = proc.get("code") or proc.get("procedure_code")
        if code:
            procedures.append(str(code))
    elif isinstance(proc, str):
        procedures.append(proc)

    canonical_claim = {
        "claim_id": claim_id,
        "submission": runtime_claim.get("submission") or {"attempt": None, "date": None},
        "case_data": {
            "case_id": claim_id,
            "patient_age": age or 0,
            "diagnoses": diagnoses,
            "procedures": procedures,
            "clinical_metrics": _extract_runtime_metrics(runtime_claim),
        },
        "evidence": _extract_runtime_evidence(runtime_claim),
    }

    return canonical_claim


generate_canonical_claim = build_canonical_claim
canonical_claim_from_runtime = build_canonical_claim
