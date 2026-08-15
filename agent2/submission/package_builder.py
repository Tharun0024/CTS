import uuid
from datetime import datetime
from typing import List
from schemas.claim import CanonicalClaim
from schemas.evidence import Evidence
from schemas.policy import CriterionEvaluation
from schemas.submission import SubmissionPackage
from submission.boundary_filter import BoundaryFilter
from validators.submission_validator import SubmissionValidator

class PackageBuilder:
    def __init__(self):
        pass

    def build_package(self, claim: CanonicalClaim, evaluations: List[CriterionEvaluation], candidate_evidence: List[Evidence]) -> SubmissionPackage:
        """Constructs a minimal SubmissionPackage and validates the trust boundary."""
        
        # 1. Filter out unreferenced evidence (Trust Boundary Enforcement)
        minimal_evidence = BoundaryFilter.filter_evidence(candidate_evidence, evaluations)
        
        # 2. Build the package
        submission_id = f"SUB-{uuid.uuid4().hex[:8].upper()}-V{claim.claim_version}"
        submitted_at = datetime.utcnow().isoformat() + "Z"
        
        package = SubmissionPackage(
            submission_id=submission_id,
            claim_id=claim.claim_id,
            claim_version=claim.claim_version,
            patient_reference=f"PAT-REF-{claim.patient_id[:8].upper()}",
            provider_reference=claim.provider_id,
            diagnosis=claim.diagnosis,
            requested_service=claim.requested_service,
            clinical_evidence=minimal_evidence,
            policy_reference=claim.policy_id,
            criterion_results=evaluations,
            submitted_at=submitted_at
        )
        
        # 3. Verify trust boundary filter programmatically
        boundary_errors = SubmissionValidator.validate_boundary_filter(package, claim.patient_id)
        if boundary_errors:
            print("Security Boundary Violations in Package Construction:")
            for err in boundary_errors:
                print(f"  - {err}")
            raise ValueError(f"Trust boundary validation failed: {boundary_errors[0]}")
            
        return package
