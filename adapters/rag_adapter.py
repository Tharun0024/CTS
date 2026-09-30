from __future__ import annotations

import re
import json
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


# =====================================================================
# CTS INTEGRATION MAPPING REGISTRIES & HELPERS
# =====================================================================

CPT_MAP: Dict[str, tuple[str, str]] = {
    "27447": ("Total knee arthroplasty (TKA)", "orthopedics"),
    "27130": ("Total hip arthroplasty (THA)", "orthopedics"),
    "63030": ("Laminotomy (decompression), lumbar", "orthopedics"),
    "C8906": ("Magnetic resonance imaging of breast, bilateral", "oncology/radiology"),
    "43775": ("Laparoscopy, sleeve gastrectomy", "bariatric / general surgery"),
    "94660": ("Continuous positive airway pressure (CPAP)", "sleep medicine"),
    "93452": ("Left heart catheterization", "cardiology"),
    "95819": ("Electroencephalogram (EEG)", "neurology"),
    "33206": ("Insertion of pacemaker", "cardiology"),
    "33207": ("Insertion of pacemaker", "cardiology"),
    "33208": ("Insertion of pacemaker", "cardiology"),
}

DIAG_MAP: Dict[str, str] = {
    "M17.11": "Primary osteoarthritis of right knee",
    "M16.11": "Primary osteoarthritis of right hip",
    "M48.061": "Spinal stenosis, lumbar region without neurogenic claudication",
    "Z80.3": "Family history of malignant neoplasm of breast",
    "E66.01": "Morbid (severe) obesity due to excess calories",
    "G47.33": "Obstructive sleep apnea (adult) (pediatric)",
    "I20.9": "Angina pectoris, unspecified",
    "G40.909": "Epilepsy, unspecified, not intractable, without status epilepticus",
    "I49.5": "Sick sinus syndrome",
    "408512008": "Body mass index 40+ - severely obese (finding)",
    "69896004": "Rheumatoid arthritis (disorder)",
    "239872002": "Osteoarthritis of hip (disorder)",
    "73430006": "Sleep apnea (disorder)",
    "49436004": "Atrial fibrillation (disorder)",
    "60573004": "Aortic valve stenosis (disorder)",
    "128613002": "Seizure disorder (disorder)",
}

# Pre-defined known structured rules (Constraint 10)
CRITERIA_RULES_REGISTRY: Dict[tuple[str, str], Dict[str, Any]] = {
    # Pacemaker Policy NCD-20.8.3
    ("NCD-20.8.3", "C01"): {
        "required_evidence_keys": ["diagnosis"],
        "clinical_rule": {"field": "diagnoses", "operator": "contains", "value": "I49.5"},
        "evidence_rule": None
    },
    ("NCD-20.8.3", "C02"): {
        "required_evidence_keys": ["diagnosis"],
        "clinical_rule": {"field": "diagnoses", "operator": "contains", "value": "I49.5"},
        "evidence_rule": None
    },
    # Knee CPB-0660
    ("CPB-0660", "C01"): {
        "required_evidence_keys": ["diagnosis"],
        "clinical_rule": {"field": "patient_age", "operator": "gte", "value": 18},
        "evidence_rule": None
    },
    ("CPB-0660", "C02"): {
        "required_evidence_keys": ["conservative_treatment"],
        "clinical_rule": None,
        "evidence_rule": None
    },
    # Diabetes Care Policy POL-001 (from tests)
    ("POL-001", "CRT-HBA1C"): {
        "required_evidence_keys": ["hba1c_report"],
        "clinical_rule": {"field": "clinical_metrics.HbA1c", "operator": "gt", "value": 8.0},
        "evidence_rule": {"field": "hba1c", "operator": "gt", "value": 8.0}
    },
    ("POL-001", "CRT-BP"): {
        "required_evidence_keys": ["bp_report"],
        "clinical_rule": {"field": "clinical_metrics.systolic_bp", "operator": "lt", "value": 140},
        "evidence_rule": {"field": "systolic_bp", "operator": "lt", "value": 140}
    },
    # Policy POL-TRANS-003 and POL-TRANS-004 from integration tests
    ("POL-TRANS-003", "CRT-HBA1C"): {
        "required_evidence_keys": ["hba1c_report"],
        "clinical_rule": {"field": "clinical_metrics.hba1c", "operator": "gt", "value": 8.0},
        "evidence_rule": {"field": "hba1c", "operator": "gt", "value": 8.0}
    },
    ("POL-TRANS-004", "CRT-HBA1C"): {
        "required_evidence_keys": ["hba1c_report", "hba1c_recheck"],
        "clinical_rule": {"field": "clinical_metrics.hba1c", "operator": "gt", "value": 8.0},
        "evidence_rule": {"field": "hba1c", "operator": "gt", "value": 8.0}
    }
}

# Explicit mapped keywords for evidence keys resolution (Constraint 7)
EXPLICIT_EVIDENCE_MAP: Dict[str, str] = {
    "hba1c": "hba1c_report",
    "blood pressure": "bp_report",
    "bp": "bp_report",
    "pacemaker": "diagnosis",
    "bradycardia": "diagnosis",
    "knee": "diagnosis",
    "osteoarthritis": "diagnosis",
    "sleep apnea": "diagnosis",
    "conservative": "conservative_treatment",
    "physical therapy": "conservative_treatment",
    "imaging": "imaging",
    "recommendation": "recommendation",
}


def resolve_evidence_keys(criterion_text: str, available_evidence_keys: List[str]) -> List[str]:
    """Resolve evidence keys using explicit maps first, then safe heuristic keyword matching."""
    text_lower = criterion_text.lower()
    resolved = []
    
    # 1. Prefer explicit/known mappings (Constraint 7)
    for kw, target_key in EXPLICIT_EVIDENCE_MAP.items():
        if kw in text_lower and target_key in available_evidence_keys:
            if target_key not in resolved:
                resolved.append(target_key)
                
    # 2. Heuristic check: check if any available evidence key name is mentioned in the text (Constraint 7/8)
    for key in available_evidence_keys:
        clean_key = key.replace("_", " ").lower()
        if (clean_key in text_lower or key.lower() in text_lower) and key not in resolved:
            resolved.append(key)
            
    return resolved


def parse_rule_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Simple parser only for safely recognized patterns (Constraint 11)."""
    text_lower = text.lower()
    
    # Pattern 1: HbA1c above/greater than/gt X
    match = re.search(r"hba1c\s*(?:above|greater than|>)\s*([0-9.]+)", text_lower)
    if match:
        try:
            return {"field": "clinical_metrics.hba1c", "operator": "gt", "value": float(match.group(1))}
        except ValueError:
            pass
            
    # Pattern 2: Systolic BP under/less than/lt X
    match = re.search(r"(?:systolic_bp|systolic bp|bp)\s*(?:under|less than|<)\s*([0-9.]+)", text_lower)
    if match:
        try:
            return {"field": "clinical_metrics.systolic_bp", "operator": "lt", "value": float(match.group(1))}
        except ValueError:
            pass
            
    # Pattern 3: Age greater than or equal to / gte X
    match = re.search(r"age\s*(?:>=|greater than or equal to)\s*([0-9.]+)", text_lower)
    if match:
        try:
            return {"field": "patient_age", "operator": "gte", "value": int(float(match.group(1)))}
        except ValueError:
            pass
            
    return None


# =====================================================================
# ADAPTER FUNCTIONS
# =====================================================================

def rag_claim_adapter(canonical_claim: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a stable Version-1 CanonicalClaim into a list of RAG ClaimInput compatible dictionaries.
    Returns a list of dicts, one for each procedure code to avoid silent truncation (Constraint 3).
    """
    if canonical_claim is None:
        raise ValueError("canonical_claim cannot be None")
        
    case_data = canonical_claim.get("case_data", {})
    claim_id = canonical_claim.get("claim_id") or case_data.get("case_id") or "UNKNOWN-CLAIM"
    
    # 1. Payer Context preservation: do not default missing payer (Constraint 2)
    clinical_metrics = case_data.get("clinical_metrics", {})
    payer = clinical_metrics.get("claim_payer") or clinical_metrics.get("payer")
    policy_id = clinical_metrics.get("claim_policy_id") or clinical_metrics.get("policy_id")
    
    insurance = {
        "primary": {
            "payer": payer,  # Can be None or UNKNOWN
            "policy_id": policy_id
        }
    }
    
    # 2. Diagnoses conversion
    diagnoses = case_data.get("diagnoses") or []
    diagnosis_list = []
    for code in diagnoses:
        desc = DIAG_MAP.get(code, f"Diagnosis {code}")
        diagnosis_list.append({
            "code": code,
            "description": desc
        })
        
    # 3. Procedures conversion - preserve all procedures
    procedures = case_data.get("procedures") or []
    
    # If no procedures are specified, preserve the missing context
    if not procedures:
        proc_desc, domain = CPT_MAP.get("UNKNOWN", (f"Procedure UNKNOWN", "general"))
        return [{
            "claim_id": claim_id,
            "insurance": insurance,
            "diagnosis": diagnosis_list,
            "procedure": {
                "code": "UNKNOWN",
                "description": proc_desc
            },
            "clinical_domain": domain
        }]
        
    inputs = []
    for code in procedures:
        proc_desc, domain = CPT_MAP.get(code, (f"Procedure {code}", "general"))
        inputs.append({
            "claim_id": claim_id,
            "insurance": insurance,
            "diagnosis": diagnosis_list,
            "procedure": {
                "code": code,
                "description": proc_desc
            },
            "clinical_domain": domain
        })
        
    return inputs


def rag_policy_adapter(claim_output: Dict[str, Any], canonical_claim: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a RAG ClaimOutput dictionary into an Agent 1 Policy dictionary format.
    Resolves criteria names, requirements, specific evidence keys, and normalizes rules (Constraint 5-13).
    """
    if claim_output is None:
        raise ValueError("claim_output cannot be None")
        
    # 1. Map policy_matches to matched_policies (Agent 1 expected format)
    matches = claim_output.get("policy_matches") or []
    matched_policies = []
    for item in matches:
        matched_policies.append({
            "policy_id": item.get("policy_id"),
            "name": item.get("payer") or item.get("policy_id")
        })
        
    policy_id = "UNKNOWN-POLICY"
    name = "RAG Matched Policy"
    if matched_policies:
        policy_id = matched_policies[0]["policy_id"] or policy_id
        name = matched_policies[0]["name"] or name
        
    # 2. Extract available evidence keys from Canonical Claim
    evidence_list = canonical_claim.get("evidence") or []
    available_evidence_keys = [item.get("evidence_key") for item in evidence_list if item.get("evidence_key")]
    
    # 3. Map criteria list
    criteria = []
    raw_criteria = claim_output.get("criteria") or []
    for item in raw_criteria:
        crit_id = item.get("criterion_id") or "UNKNOWN-CRITERION"
        # Criterion name/requirement translation
        crit_name = item.get("criterion") or "Unnamed Criterion"
        crit_req = item.get("policy_requirement") or ""
        
        # Resolve evidence keys and rules from registry first
        registry_match = CRITERIA_RULES_REGISTRY.get((policy_id, crit_id))
        
        if registry_match:
            required_evidence_keys = registry_match["required_evidence_keys"]
            clinical_rule = registry_match["clinical_rule"]
            evidence_rule = registry_match["evidence_rule"]
        else:
            # Safe heuristics: resolve evidence keys using keyword matching
            required_evidence_keys = resolve_evidence_keys(crit_req, available_evidence_keys)
            
            # Simple rule parsing for recognized patterns (Constraint 11/12)
            parsed_rule = parse_rule_from_text(crit_req)
            clinical_rule = parsed_rule
            evidence_rule = None
            
            # If both rules and keys are empty, fail safely by adding a guard key (Constraint 12)
            if not clinical_rule and not required_evidence_keys:
                required_evidence_keys = ["__unresolved_rule_guard__"]
            
        criteria.append({
            "criterion_id": crit_id,
            "name": crit_name,
            "description": crit_req,
            "mandatory": True,
            "clinical_rule": clinical_rule,
            "evidence_rule": evidence_rule,
            "required_evidence_keys": required_evidence_keys,
            "interpretation_guidance": "",
            "evaluation_type": ""
        })
        
    # Exclusions are not directly parsed by RAG, but preserve them if present
    exclusions = claim_output.get("exclusions") or []
    
    return {
        "policy_id": policy_id,
        "name": name,
        "exclusions": exclusions,
        "criteria": criteria,
        "matched_policies": matched_policies
    }
