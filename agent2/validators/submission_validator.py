from typing import List
from schemas.submission import SubmissionPackage

class SubmissionValidator:
    """Enforces patient safety and trust boundaries before a package is sent to the payer."""
    
    @staticmethod
    def validate_boundary_filter(package: SubmissionPackage, expected_patient_id: str) -> List[str]:
        errors = []

        # 1. Ensure all evidence belongs to the expected patient
        for ev in package.clinical_evidence:
            if ev.patient_id != expected_patient_id:
                errors.append(
                    f"Security Alert: Evidence '{ev.evidence_id}' belongs to patient ID '{ev.patient_id}' instead of expected '{expected_patient_id}'."
                )

        # 2. Enforce Minimal Evidence Package (Rule 9)
        # Collect all evidence IDs referenced in the evaluations
        referenced_ids = set()
        for c_res in package.criterion_results:
            for eid in c_res.patient_evidence_ids:
                referenced_ids.add(eid)

        # Collect evidence IDs physically present in the package's clinical_evidence list
        included_ids = {ev.evidence_id for ev in package.clinical_evidence}

        # Check for unreferenced evidence leaks (violations of trust boundary)
        for ev in package.clinical_evidence:
            if ev.evidence_id not in referenced_ids:
                errors.append(
                    f"Trust Boundary Leak: Evidence '{ev.evidence_id}' ({ev.source_type}) is packaged but not referenced by any criterion."
                )

        # Check for referenced evidence that is missing from the package list
        for rid in referenced_ids:
            if rid not in included_ids:
                errors.append(
                    f"Data Inconsistency: Evidence '{rid}' is referenced in evaluations but is missing from the package clinical evidence list."
                )

        return errors
