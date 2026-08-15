from typing import List
from schemas.evidence import Evidence

class EvidenceValidator:
    """Validates that clinical evidence references are real and correspond to retrieved records."""
    
    @staticmethod
    def validate_evidence_existence(evidence_list: List[Evidence], linked_evidence_ids: List[str]) -> List[str]:
        """Returns list of evidence IDs that were referenced but do not exist in the candidate list."""
        existing_ids = {e.evidence_id for e in evidence_list}
        invalid_ids = []
        for eid in linked_evidence_ids:
            if eid not in existing_ids:
                invalid_ids.append(eid)
        return invalid_ids
