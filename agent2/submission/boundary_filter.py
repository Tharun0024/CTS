from typing import List
from schemas.evidence import Evidence
from schemas.policy import CriterionEvaluation

class BoundaryFilter:
    """Enforces the trust boundary by filtering out unreferenced clinical evidence."""
    
    @staticmethod
    def filter_evidence(evidence_list: List[Evidence], evaluations: List[CriterionEvaluation]) -> List[Evidence]:
        """Returns only the patient evidence records that are explicitly referenced in satisfied/uncertain criteria."""
        referenced_ids = set()
        for eval_result in evaluations:
            # We only package evidence for criteria that are evaluated (satisfied or even uncertain)
            for eid in eval_result.patient_evidence_ids:
                if isinstance(eid, str):
                    referenced_ids.add(eid)

        # Clean list to avoid weird types
        clean_referenced_ids = {rid for rid in referenced_ids if rid}
        
        filtered = [ev for ev in evidence_list if ev.evidence_id in clean_referenced_ids]
        return filtered
