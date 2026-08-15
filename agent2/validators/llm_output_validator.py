from typing import List
from schemas.policy import CriterionEvaluation
from validators.evidence_validator import EvidenceValidator
from schemas.evidence import Evidence

class LLMOutputValidator:
    """Validates the structure and logical consistency of the LLM's criterion evaluations."""
    
    @staticmethod
    def validate_evaluations(evaluations: List[CriterionEvaluation], candidate_evidence: List[Evidence]) -> List[str]:
        errors = []
        
        for eval_result in evaluations:
            cid = eval_result.criterion_id
            status = eval_result.status
            evidence_ids = eval_result.patient_evidence_ids
            
            # Rule 6 check: If SATISFIED, there must be at least one clinical evidence reference.
            if status == "SATISFIED" and not evidence_ids:
                errors.append(
                    f"Criterion '{cid}' is marked as 'SATISFIED' but has zero supporting patient evidence IDs."
                )
                
            # Verify that linked evidence IDs exist in the candidate list
            if evidence_ids:
                invalid_ids = EvidenceValidator.validate_evidence_existence(candidate_evidence, evidence_ids)
                if invalid_ids:
                    errors.append(
                        f"Criterion '{cid}' references non-existent evidence IDs: {', '.join(invalid_ids)}"
                    )
                    
        return errors
