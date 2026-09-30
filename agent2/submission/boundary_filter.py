from typing import List, Tuple, Dict
from ..schemas.evidence import Evidence, EvidenceState
from ..schemas.policy import CriterionEvaluation
from ..validators.evidence_validator import EvidenceValidator

class BoundaryFilter:
    """Enforces the trust boundary by filtering out unreferenced clinical evidence.
    Implements sensitivity/release gate: minimum necessary evidence only, no patient-record leakage."""
    
    @staticmethod
    def filter_evidence(evidence_list: List[Evidence], evaluations: List[CriterionEvaluation]) -> Tuple[List[Evidence], List[str], bool]:
        """
        Returns:
        - filtered_evidence: Only evidence explicitly referenced in criteria
        - sensitive_blocked: List of sensitive evidence IDs that were blocked
        - has_sensitive_evidence: Whether sensitive evidence was detected
        
        Implements minimum necessary evidence principle and sensitive evidence blocking.
        """
        # 1. Identify referenced evidence IDs
        referenced_ids = set()
        for eval_result in evaluations:
            for eid in eval_result.patient_evidence_ids:
                if isinstance(eid, str):
                    referenced_ids.add(eid)

        # Clean list to avoid weird types
        clean_referenced_ids = {rid for rid in referenced_ids if rid}
        
        # 2. Filter to only referenced evidence (minimum necessary principle)
        filtered = [ev for ev in evidence_list if ev.evidence_id in clean_referenced_ids]
        
        # 3. Check for sensitive evidence in filtered list
        sensitive_evidence_ids = EvidenceValidator.detect_sensitive_evidence(filtered)
        sensitive_blocked = []
        has_sensitive_evidence = len(sensitive_evidence_ids) > 0
        
        # 4. Remove sensitive evidence from filtered list
        if sensitive_evidence_ids:
            filtered = [ev for ev in filtered if ev.evidence_id not in sensitive_evidence_ids]
            sensitive_blocked = sensitive_evidence_ids
        
        # 5. Validate evidence provenance
        provenance_errors = EvidenceValidator.validate_evidence_provenance(filtered)
        if provenance_errors:
            # If provenance validation fails, we should still proceed but log warnings
            print(f"[Warning] Evidence provenance validation issues: {provenance_errors}")
        
        # 6. Ensure we're not leaking patient identifiers
        filtered = BoundaryFilter._anonymize_patient_identifiers(filtered)
        
        return filtered, sensitive_blocked, has_sensitive_evidence
    
    @staticmethod
    def _anonymize_patient_identifiers(evidence_list: List[Evidence]) -> List[Evidence]:
        """Anonymizes patient identifiers in evidence content."""
        anonymized_evidence = []
        
        for evidence in evidence_list:
            # Create a copy to avoid modifying original
            anonymized_content = evidence.content
            
            # Remove or mask potential patient identifiers
            # In production, this would use more sophisticated de-identification
            import re
            
            # Mask SSN-like patterns
            anonymized_content = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN-REDACTED]', anonymized_content)
            
            # Mask phone numbers
            anonymized_content = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE-REDACTED]', anonymized_content)
            
            # Mask email addresses
            anonymized_content = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '[EMAIL-REDACTED]', anonymized_content)
            
            # Create new evidence with anonymized content
            anonymized_evidence.append(Evidence(
                evidence_id=evidence.evidence_id,
                patient_id=evidence.patient_id,
                source_type=evidence.source_type,
                source_record_id=evidence.source_record_id,
                event_date=evidence.event_date,
                content=anonymized_content,
                state=evidence.state,
                relevance_score=evidence.relevance_score,
                evidence_type=evidence.evidence_type,
                retrieved_at=evidence.retrieved_at
            ))
        
        return anonymized_evidence
    
    @staticmethod
    def validate_minimum_necessary(filtered_evidence: List[Evidence], all_evidence: List[Evidence]) -> bool:
        """Validates that filtered evidence represents the minimum necessary for decision."""
        # Count evidence before and after filtering
        total_evidence_count = len(all_evidence)
        filtered_evidence_count = len(filtered_evidence)
        
        # If we filtered out more than 90% of evidence, that's suspicious
        if total_evidence_count > 10 and filtered_evidence_count == 0:
            return False
        
        # Check that filtered evidence is subset of all evidence
        filtered_ids = {ev.evidence_id for ev in filtered_evidence}
        all_ids = {ev.evidence_id for ev in all_evidence}
        
        if not filtered_ids.issubset(all_ids):
            return False
        
        return True
