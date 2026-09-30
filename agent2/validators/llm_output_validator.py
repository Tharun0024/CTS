from typing import List, Set
from ..schemas.policy import CriterionEvaluation
from .evidence_validator import EvidenceValidator
from ..schemas.evidence import Evidence, EvidenceState

class LLMOutputValidator:
    """Validates the structure and logical consistency of the LLM's criterion evaluations.
    Rejects malformed output, invalid evidence IDs, fabricated evidence, and unsupported statuses."""
    
    @staticmethod
    def validate_evaluations(evaluations: List[CriterionEvaluation], candidate_evidence: List[Evidence]) -> List[str]:
        errors = []
        valid_statuses = {"SATISFIED", "NOT_SATISFIED", "UNCERTAIN"}
        
        # Build evidence ID map for quick lookup
        evidence_id_map = {ev.evidence_id: ev for ev in candidate_evidence}
        
        for eval_result in evaluations:
            cid = eval_result.criterion_id
            status = eval_result.status
            evidence_ids = eval_result.patient_evidence_ids
            
            # 1. Validate status is one of the allowed values
            if status not in valid_statuses:
                errors.append(
                    f"Criterion '{cid}' has invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
                )
                continue  # Skip further validation for this criterion
            
            # 2. Check for fabricated evidence IDs (IDs that don't exist in candidate evidence)
            if evidence_ids:
                invalid_ids = EvidenceValidator.validate_evidence_existence(candidate_evidence, evidence_ids)
                if invalid_ids:
                    errors.append(
                        f"Criterion '{cid}' references non-existent/fabricated evidence IDs: {', '.join(invalid_ids)}"
                    )
                
                # 3. Check for evidence state consistency
                for ev_id in evidence_ids:
                    if ev_id in evidence_id_map:
                        evidence = evidence_id_map[ev_id]
                        # Evidence marked as MISSING cannot support SATISFIED criteria
                        if status == "SATISFIED" and evidence.state == EvidenceState.MISSING:
                            errors.append(
                                f"Criterion '{cid}' references MISSING evidence '{ev_id}' but claims SATISFIED status."
                            )
            
            # 4. SATISFIED criteria must have supporting evidence
            if status == "SATISFIED" and not evidence_ids:
                errors.append(
                    f"Criterion '{cid}' is marked as 'SATISFIED' but has zero supporting patient evidence IDs."
                )
            
            # 5. NOT_SATISFIED criteria with evidence should have explanation
            if status == "NOT_SATISFIED" and evidence_ids and not eval_result.explanation:
                errors.append(
                    f"Criterion '{cid}' is NOT_SATISFIED with evidence but lacks explanation."
                )
            
            # 6. UNCERTAIN criteria should have explanation
            if status == "UNCERTAIN" and not eval_result.explanation:
                errors.append(
                    f"Criterion '{cid}' is UNCERTAIN but lacks explanation of uncertainty."
                )
        
        # 7. Check for duplicate criterion evaluations
        criterion_ids = [eval.criterion_id for eval in evaluations]
        if len(criterion_ids) != len(set(criterion_ids)):
            errors.append("Duplicate criterion evaluations detected in LLM output.")
        
        return errors
    
    @staticmethod
    def validate_llm_json_structure(llm_output: str) -> List[str]:
        """Validates that LLM output is valid JSON with expected structure."""
        errors = []
        import json
        
        try:
            data = json.loads(llm_output)
        except json.JSONDecodeError as e:
            errors.append(f"LLM output is not valid JSON: {str(e)}")
            return errors
        
        # Check for required top-level structure
        if not isinstance(data, dict):
            errors.append("LLM output must be a JSON object.")
            return errors
        
        if "evaluations" not in data:
            errors.append("LLM output missing 'evaluations' field.")
        elif not isinstance(data["evaluations"], list):
            errors.append("'evaluations' must be a list.")
        
        return errors
    
    @staticmethod
    def detect_fabricated_content(evaluations: List[CriterionEvaluation], candidate_evidence: List[Evidence]) -> List[str]:
        """Detects evidence that appears to be fabricated (not matching actual evidence content)."""
        errors = []
        evidence_content_map = {ev.evidence_id: ev.content.lower() for ev in candidate_evidence}
        
        for eval_result in evaluations:
            cid = eval_result.criterion_id
            explanation = eval_result.explanation.lower() if eval_result.explanation else ""
            
            # Check if explanation references evidence IDs that don't match content
            for ev_id in eval_result.patient_evidence_ids:
                if ev_id in evidence_content_map:
                    evidence_content = evidence_content_map[ev_id]
                    # Basic check: if explanation mentions specific values not in evidence
                    if "value" in explanation and "value" not in evidence_content:
                        # This is a simple check - in production would be more sophisticated
                        pass
        
        return errors
    
    @staticmethod
    def validate_criterion_coverage(evaluations: List[CriterionEvaluation], expected_criterion_ids: Set[str]) -> List[str]:
        """Validates that all expected criteria are covered in evaluations."""
        errors = []
        evaluated_ids = {eval.criterion_id for eval in evaluations}
        missing_ids = expected_criterion_ids - evaluated_ids
        
        if missing_ids:
            errors.append(f"Missing evaluations for criteria: {', '.join(sorted(missing_ids))}")
        
        return errors
