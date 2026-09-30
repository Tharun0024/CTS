from pydantic import BaseModel, Field
from typing import List
from .claim import DiagnosisInfo, ServiceInfo
from .evidence import Evidence
from .policy import CriterionEvaluation

class SubmissionPackage(BaseModel):
    submission_id: str = Field(description="Unique identifier for the submission package")
    claim_id: str = Field(description="Reference to the claim ID")
    claim_version: int = Field(description="Version of the claim submitted")
    patient_reference: str = Field(description="Reference ID of the patient (crosses boundary)")
    provider_reference: str = Field(description="Reference ID of the provider")
    diagnosis: DiagnosisInfo = Field(description="Compact diagnosis representation")
    requested_service: ServiceInfo = Field(description="Requested procedure/medication details")
    clinical_evidence: List[Evidence] = Field(description="The minimal clinical evidence package required to prove compliance (unrelated records filtered out)")
    policy_reference: str = Field(description="Reference identifier of the coverage policy used")
    criterion_results: List[CriterionEvaluation] = Field(description="Evaluations demonstrating compliance status")
    submitted_at: str = Field(description="Timestamp in ISO format")
