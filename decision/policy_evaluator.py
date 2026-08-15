from typing import Any, Dict, List, Optional
from decision.schemas import CaseData, PolicyExclusion, PolicyCriterion, Rule


def validate_rule(rule: Rule) -> bool:
    """
    Validates that a Rule object is properly structured and uses a supported operator.
    """
    if not isinstance(rule, Rule):
        return False
    if not rule.field or not isinstance(rule.field, str):
        return False
    if not rule.operator or not isinstance(rule.operator, str):
        return False
    supported_operators = {"eq", "ne", "lt", "lte", "gt", "gte", "contains", "not_contains", "in", "not_in"}
    if rule.operator.lower().strip() not in supported_operators:
        return False
    return True


def resolve_field_value(field_path: str, data: Any) -> Any:
    """
    Traverses dicts and objects to extract a nested value based on a dot-separated path.
    E.g. "clinical_metrics.HbA1c" on CaseData extracts data.clinical_metrics["HbA1c"].
    Fails safely and returns None if path elements are missing.
    """
    if not field_path:
        return None

    parts = field_path.split(".")
    current = data
    for part in parts:
        if current is None:
            return None

        if isinstance(current, dict):
            if part not in current:
                return None
            current = current.get(part)
        elif hasattr(current, "__dict__") and hasattr(current, part):
            current = getattr(current, part)
        else:
            try:
                current = getattr(current, part)
            except AttributeError:
                return None
    return current


def icd_code_matches(code: str, prefix: str) -> bool:
    """
    Performs safety-hardened prefix matching for ICD codes to prevent false positives.
    E.g. prefix "E10" matches "E10" and "E10.9", but does NOT match "E100".
    """
    if not isinstance(code, str) or not isinstance(prefix, str):
        return False
    return code == prefix or code.startswith(prefix + ".")


def check_operator(resolved_val: Any, operator: str, expected_val: Any) -> bool:
    """
    Compares the field value to the expected value using the specified operator.
    Handles type mismatches, None values, and lists safely.
    """
    if resolved_val is None:
        if operator == "eq":
            return expected_val is None
        elif operator == "ne":
            return expected_val is not None
        # Any other comparisons (gt, lt, contains, etc.) against a null value are False
        return False

    try:
        op = operator.lower().strip()
        
        # 1. Equality check
        if op == "eq":
            return resolved_val == expected_val
        elif op == "ne":
            return resolved_val != expected_val

        # 2. Ordered comparison (fails safely on type mismatches)
        elif op in {"lt", "lte", "gt", "gte"}:
            if type(resolved_val) is not type(expected_val) and not (
                isinstance(resolved_val, (int, float)) and isinstance(expected_val, (int, float))
            ):
                return False  # Do not compare incompatible types
            
            if op == "lt":
                return resolved_val < expected_val
            elif op == "lte":
                return resolved_val <= expected_val
            elif op == "gt":
                return resolved_val > expected_val
            elif op == "gte":
                return resolved_val >= expected_val

        # 3. Contains check (handles lists of codes with safe ICD code prefix check, and strings)
        elif op == "contains":
            if isinstance(resolved_val, (list, set, tuple)):
                if isinstance(expected_val, str):
                    # Smart ICD matching if items are strings
                    return any(isinstance(val, str) and icd_code_matches(val, expected_val) for val in resolved_val)
                return expected_val in resolved_val
            elif isinstance(resolved_val, str) and isinstance(expected_val, str):
                return expected_val.lower() in resolved_val.lower()
            elif hasattr(resolved_val, "__contains__"):
                return expected_val in resolved_val
            return False

        elif op == "not_contains":
            if isinstance(resolved_val, (list, set, tuple)):
                if isinstance(expected_val, str):
                    return not any(isinstance(val, str) and icd_code_matches(val, expected_val) for val in resolved_val)
                return expected_val not in resolved_val
            elif isinstance(resolved_val, str) and isinstance(expected_val, str):
                return expected_val.lower() not in resolved_val.lower()
            elif hasattr(resolved_val, "__contains__"):
                return expected_val not in resolved_val
            return True

        # 4. In checks
        elif op == "in":
            if isinstance(expected_val, (list, set, tuple)):
                if isinstance(resolved_val, str):
                    return any(isinstance(val, str) and icd_code_matches(resolved_val, val) for val in expected_val)
                return resolved_val in expected_val
            if hasattr(expected_val, "__contains__"):
                return resolved_val in expected_val
            return False

        elif op == "not_in":
            if isinstance(expected_val, (list, set, tuple)):
                if isinstance(resolved_val, str):
                    return not any(isinstance(val, str) and icd_code_matches(resolved_val, val) for val in expected_val)
                return resolved_val not in expected_val
            if hasattr(expected_val, "__contains__"):
                return resolved_val not in expected_val
            return True

        else:
            return False
            
    except (TypeError, ValueError, AttributeError):
        return False


def evaluate_rule(rule: Rule, data: Any) -> bool:
    """
    Resolves the field on the data object/dict and evaluates it against the rule.
    Safe-fails and returns False if the rule is invalid or an exception occurs.
    """
    if not validate_rule(rule):
        raise ValueError(f"Invalid rule definition: {rule}")
    resolved = resolve_field_value(rule.field, data)
    return check_operator(resolved, rule.operator, rule.value)


def evaluate_exclusions(case_data: CaseData, exclusions: List[PolicyExclusion]) -> Dict[str, bool]:
    """
    Checks each exclusion rule against CaseData. Returns a dict mapping exclusion_id to
    whether it triggered (True means patient is excluded).
    """
    results = {}
    for exclusion in exclusions:
        results[exclusion.exclusion_id] = evaluate_rule(exclusion.rule, case_data)
    return results


def evaluate_clinical_criteria(case_data: CaseData, criteria: List[PolicyCriterion]) -> Dict[str, bool]:
    """
    Checks each criterion's clinical rule against CaseData.
    If no clinical rule is defined, it is considered True (passed clinical check).
    """
    results = {}
    for criterion in criteria:
        if criterion.clinical_rule is None:
            results[criterion.criterion_id] = True
        else:
            results[criterion.criterion_id] = evaluate_rule(criterion.clinical_rule, case_data)
    return results
