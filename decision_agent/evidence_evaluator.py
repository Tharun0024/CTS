from typing import Dict, List, Any, Optional
from decision_agent.schemas import PolicyCriterion, PolicyExclusion, EvidenceItem, EvidenceStatus
from decision_agent.policy_evaluator import evaluate_rule, validate_rule


# Severity of status flags for prioritizing what status is returned
STATUS_SEVERITY = {
    "contradictory": 6,
    "ambiguous": 5,
    "unverified": 4,
    "low_confidence": 3,
    "failed_validation": 2,
    "missing": 1,
    "verified": 0,
}


def find_group_conflict(items: List[EvidenceItem]) -> Optional[str]:
    """
    Checks if multiple evidence items for the same key contain conflicting facts.
    Returns "contradictory" if there's a discrepancy in their extracted_facts.
    """
    if len(items) <= 1:
        return None
    
    first_facts = items[0].extracted_facts
    for item in items[1:]:
        if item.extracted_facts != first_facts:
            return "contradictory"
    return None


def evaluate_evidence_group(
    evidence_key: str,
    items: List[EvidenceItem],
    evidence_rule: Optional[Any] = None,
    confidence_threshold: float = 0.7
) -> str:
    """
    Evaluates list of evidence items provided for a single key against security parameters
    and an optional validation rule.
    """
    if not items:
        return "missing"

    # 1. Check for contradictory status flag in any item
    if any(item.status == EvidenceStatus.CONTRADICTORY for item in items):
        return "contradictory"

    # 2. Check for explicit ambiguity flag in any item
    if any(item.is_ambiguous for item in items):
        return "ambiguous"

    # 3. Check for fact discrepancy among duplicate items
    if find_group_conflict(items) is not None:
        return "contradictory"

    # 4. Check for unverified status in any item
    if any(item.status == EvidenceStatus.UNVERIFIED for item in items):
        return "unverified"

    # 5. Check for confidence rating below threshold
    if any(item.confidence_score < confidence_threshold for item in items):
        return "low_confidence"

    # 6. Evaluate validation rule against extracted facts (using first item since they are identical if no conflict)
    if evidence_rule is not None:
        try:
            if not evaluate_rule(evidence_rule, items[0].extracted_facts):
                return "failed_validation"
        except Exception:
            # If evaluation throws (e.g. malformed comparison, missing path), fail validation closed
            return "failed_validation"

    return "verified"


def evaluate_all_evidence(
    criteria: List[PolicyCriterion],
    exclusions: List[PolicyExclusion],
    evidence_list: List[EvidenceItem],
    confidence_threshold: float = 0.7
) -> Dict[str, str]:
    """
    Groups evidence list by key, evaluates each group against rules in criteria and exclusions,
    and returns a summary status map. Resolves status collisions using status severity weighting.
    """
    # Group evidence items by their key
    evidence_groups: Dict[str, List[EvidenceItem]] = {}
    for item in evidence_list:
        evidence_groups.setdefault(item.evidence_key, []).append(item)

    evidence_status: Dict[str, str] = {}

    def update_status(key: str, status: str):
        if key in evidence_status:
            old_val = evidence_status[key]
            if STATUS_SEVERITY.get(status, 0) > STATUS_SEVERITY.get(old_val, 0):
                evidence_status[key] = status
        else:
            evidence_status[key] = status

    # Evaluate criteria requirements
    for criterion in criteria:
        for key in criterion.required_evidence_keys:
            group_items = evidence_groups.get(key, [])
            status = evaluate_evidence_group(key, group_items, criterion.evidence_rule, confidence_threshold)
            update_status(key, status)

    # Evaluate exclusion requirements
    for exclusion in exclusions:
        for key in exclusion.required_evidence_keys:
            group_items = evidence_groups.get(key, [])
            status = evaluate_evidence_group(key, group_items, getattr(exclusion, "evidence_rule", None), confidence_threshold)
            update_status(key, status)

    return evidence_status
