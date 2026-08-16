import uuid
from datetime import datetime
from typing import List, Tuple, Optional
from ..schemas.claim import CanonicalClaim
from ..schemas.evidence import Evidence
from ..schemas.policy import CriterionEvaluation
from ..schemas.submission import SubmissionPackage
from .boundary_filter import BoundaryFilter
from ..validators.submission_validator import SubmissionValidator

class PackageBuilder:
    def __init__(self):
        pass

    def build_package(self, claim: CanonicalClaim, evaluations: List[CriterionEvaluation], candidate_evidence: List[Evidence]) -> Tuple[Optional[SubmissionPackage], bool, List[str]]:
        """
        Constructs a minimal SubmissionPackage with sensitivity/release gate.
        
        Returns:
        - package: SubmissionPackage if build successful, None if blocked by sensitive evidence
        - has_sensitive_evidence: Whether sensitive evidence was detected and blocked
        - sensitive_blocked: List of sensitive evidence IDs that were blocked
        """
        
        # 1. Filter evidence with sensitivity gate
        minimal_evidence, sensitive_blocked, has_sensitive_evidence = BoundaryFilter.filter_evidence(
            candidate_evidence, evaluations
        )
        
        # 2. If sensitive evidence was blocked, return None package (escalate to HUMAN_REVIEW)
        if has_sensitive_evidence:
            print(f"[Security] Sensitive evidence blocked: {sensitive_blocked}. Escalating to HUMAN_REVIEW.")
            return None, has_sensitive_evidence, sensitive_blocked
        
        # 3. Validate minimum necessary principle
        if not BoundaryFilter.validate_minimum_necessary(minimal_evidence, candidate_evidence):
            print("[Warning] Minimum necessary validation failed. Package may contain unnecessary evidence.")
        
        # 4. Build the package
        submission_id = f"SUB-{uuid.uuid4().hex[:8].upper()}-V{claim.claim_version}"
        submitted_at = datetime.utcnow().isoformat() + "Z"
        
        # Use anonymized patient reference
        patient_reference = f"PAT-REF-{claim.patient_id[:8].upper()}"
        
        package = SubmissionPackage(
            submission_id=submission_id,
            claim_id=claim.claim_id,
            claim_version=claim.claim_version,
            patient_reference=patient_reference,
            provider_reference=claim.provider_id,
            diagnosis=claim.diagnosis,
            requested_service=claim.requested_service,
            clinical_evidence=minimal_evidence,
            policy_reference=claim.policy_id,
            criterion_results=evaluations,
            submitted_at=submitted_at
        )
        
        # 5. Verify trust boundary filter programmatically
        boundary_errors = SubmissionValidator.validate_boundary_filter(package, claim.patient_id)
        if boundary_errors:
            print("Security Boundary Violations in Package Construction:")
            for err in boundary_errors:
                print(f"  - {err}")
            raise ValueError(f"Trust boundary validation failed: {boundary_errors[0]}")
            
        return package, has_sensitive_evidence, sensitive_blocked
    
    def build_recovery_package(self, claim: CanonicalClaim, evaluations: List[CriterionEvaluation], 
                              recovered_evidence: List[Evidence], original_evidence: List[Evidence]) -> Tuple[Optional[SubmissionPackage], bool, List[str]]:
        """
        Specialized package builder for recovery/resubmission scenarios.
        Ensures only new/recovered evidence is included, not previously submitted evidence.
        """
        # For recovery, we only include evidence that supports newly satisfied criteria
        # or evidence that was missing in previous submission
        
        # Filter to only include evidence relevant to recovery
        recovery_relevant_evidence = []
        for evidence in recovered_evidence:
            # Include evidence that was previously MISSING and is now FOUND
            if evidence.state == EvidenceState.FOUND and evidence.evidence_id.startswith("EV-MISSING-"):
                # This was a missing concept that we found
                recovery_relevant_evidence.append(evidence)
            # Include evidence that supports newly satisfied criteria
            # (This would require tracking which criteria changed status)
        
        # If no recovery-relevant evidence, we shouldn't resubmit
        if not recovery_relevant_evidence:
            return None, False, []
        
        # Build package with only recovery-relevant evidence
        return self.build_package(claim, evaluations, recovery_relevant_evidence)
