from typing import List, Dict, Set
from ..schemas.evidence import Evidence, EvidenceState

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
    
    @staticmethod
    def validate_evidence_state_constraints(evaluations: List[Dict], evidence_list: List[Evidence]) -> List[str]:
        """Validates that evidence state constraints are respected."""
        errors = []
        evidence_map = {ev.evidence_id: ev for ev in evidence_list}
        
        for eval_data in evaluations:
            criterion_id = eval_data.get("criterion_id", "")
            status = eval_data.get("status", "")
            evidence_ids = eval_data.get("patient_evidence_ids", [])
            
            for ev_id in evidence_ids:
                if ev_id in evidence_map:
                    evidence = evidence_map[ev_id]
                    # MISSING evidence cannot support SATISFIED criteria
                    if status == "SATISFIED" and evidence.state == EvidenceState.MISSING:
                        errors.append(
                            f"Criterion '{criterion_id}' claims SATISFIED but references MISSING evidence '{ev_id}'"
                        )
        
        return errors
    
    @staticmethod
    def detect_sensitive_evidence(evidence_list: List[Evidence]) -> List[str]:
        """Detects evidence that may contain sensitive information."""
        sensitive_terms = [
            "ssn", "social security", "credit card", "bank account", 
            "password", "secret", "confidential", "psychiatric", 
            "substance abuse", "hiv", "aids", "mental health"
        ]
        
        sensitive_evidence = []
        for evidence in evidence_list:
            content_lower = evidence.content.lower()
            for term in sensitive_terms:
                if term in content_lower:
                    sensitive_evidence.append(evidence.evidence_id)
                    break
        
        return sensitive_evidence
    
    @staticmethod
    def validate_evidence_provenance(evidence_list: List[Evidence]) -> List[str]:
        """Validates that evidence has proper provenance (source record IDs, dates)."""
        errors = []
        for evidence in evidence_list:
            if not evidence.source_record_id and evidence.state == EvidenceState.FOUND:
                errors.append(f"Evidence '{evidence.evidence_id}' is FOUND but has no source_record_id")
            if not evidence.event_date and evidence.state == EvidenceState.FOUND:
                errors.append(f"Evidence '{evidence.evidence_id}' is FOUND but has no event_date")
            if evidence.evidence_id.startswith("EV-MISSING-") and evidence.state != EvidenceState.MISSING:
                errors.append(f"Evidence '{evidence.evidence_id}' has MISSING prefix but state is {evidence.state}")
        
        return errors
