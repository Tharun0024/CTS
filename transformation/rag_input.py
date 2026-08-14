from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping


def _coerce_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_criterion(raw_criterion: Mapping[str, Any]) -> Dict[str, Any]:
    required_evidence = raw_criterion.get("required_evidence") or raw_criterion.get("required_evidence_keys") or []
    required_evidence_keys = _coerce_list(required_evidence)

    return {
        "criterion_id": raw_criterion.get("criterion_id") or raw_criterion.get("id") or "UNKNOWN-CRITERION",
        "name": raw_criterion.get("name") or raw_criterion.get("requirement") or "Unnamed Criterion",
        "description": raw_criterion.get("description") or raw_criterion.get("requirement") or "",
        "mandatory": bool(raw_criterion.get("mandatory", True)),
        "applicability_rule": raw_criterion.get("applicability_rule"),
        "required_evidence_keys": required_evidence_keys,
        "interpretation_guidance": raw_criterion.get("interpretation_guidance", ""),
        "required_evidence": required_evidence_keys,
        "evaluation_type": raw_criterion.get("evaluation_type", ""),
        "clinical_rule": raw_criterion.get("clinical_rule"),
        "evidence_rule": raw_criterion.get("evidence_rule"),
    }


def build_rag_policy(runtime_policy: Mapping[str, Any]) -> Dict[str, Any]:
    """Convert Version-1 runtime policy data into the current Agent-1 RAG policy contract."""
    if runtime_policy is None:
        raise ValueError("runtime_policy cannot be None")

    if "policy_id" in runtime_policy and "criteria" in runtime_policy:
        return deepcopy(dict(runtime_policy))

    matched_policies = runtime_policy.get("matched_policies") or []
    policy_info = matched_policies[0] if isinstance(matched_policies, list) and matched_policies else {}

    raw_criteria = runtime_policy.get("criteria") or runtime_policy.get("rag_criteria") or []
    normalized_criteria = [_normalize_criterion(item) for item in raw_criteria if isinstance(item, Mapping)]

    policy_id = runtime_policy.get("policy_id") or policy_info.get("policy_id") or "UNKNOWN-POLICY"
    name = runtime_policy.get("name") or policy_info.get("name") or policy_id

    return {
        "policy_id": policy_id,
        "name": name,
        "exclusions": [deepcopy(item) for item in _coerce_list(runtime_policy.get("exclusions")) if isinstance(item, Mapping)],
        "criteria": normalized_criteria,
    }


generate_rag_policy = build_rag_policy
rag_policy_from_runtime = build_rag_policy
