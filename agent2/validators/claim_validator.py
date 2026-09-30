from typing import List, Dict
from ..schemas.claim import CanonicalClaim
from ..database.repositories.patient_repository import PatientRepository

class ClaimValidator:
    def __init__(self):
        self.patient_repo = PatientRepository()

    def validate_claim(self, claim: CanonicalClaim) -> List[str]:
        """Validates the Canonical Claim details deterministically."""
        errors = []

        # 1. Schema Validation (handled by Pydantic mostly, but we check specific values)
        if not claim.claim_id:
            errors.append("Claim ID is missing.")
        if not claim.patient_id:
            errors.append("Patient ID is missing.")
        if not claim.provider_id:
            errors.append("Provider ID is missing.")
        if not claim.payer_id:
            errors.append("Payer ID is missing.")
        if not claim.policy_id:
            errors.append("Policy ID reference is missing.")
            
        # 2. Database Existence Validation
        if claim.patient_id:
            patient = self.patient_repo.get_patient(claim.patient_id)
            if not patient:
                errors.append(f"Patient with ID '{claim.patient_id}' does not exist in the database.")

        # 3. Diagnosis and Service validation
        if not claim.diagnosis.code or not claim.diagnosis.description:
            errors.append("Claim must contain a valid diagnosis code and description.")
        if not claim.requested_service.procedure_code or not claim.requested_service.procedure_name:
            errors.append("Claim must contain a valid requested service/procedure code and name.")
            
        # 4. Payer Type Validation
        if claim.payer_type.upper() not in ["COMMERCIAL", "MEDICARE", "MEDICAID"]:
            errors.append(f"Invalid payer type: '{claim.payer_type}'. Must be COMMERCIAL, MEDICARE, or MEDICAID.")

        return errors
