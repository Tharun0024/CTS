from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class DiagnosisInfo(BaseModel):
    code: str = Field(description="The medical diagnosis code (e.g. SNOMED or ICD-10)")
    description: str = Field(description="The description of the diagnosis")

class ServiceInfo(BaseModel):
    procedure_code: str = Field(description="The procedure or service code (e.g. CPT or HCPCS)")
    procedure_name: str = Field(description="The name/description of the requested service")

class CanonicalClaim(BaseModel):
    claim_id: str = Field(description="Unique claim identifier")
    claim_version: int = Field(default=1, description="Version of the claim (increments on resubmission)")
    patient_id: str = Field(description="Unique patient identifier")
    provider_id: str = Field(description="Unique healthcare provider/facility identifier")
    payer_id: str = Field(description="Unique health plan/payer identifier")
    payer_type: str = Field(description="Type of payer, e.g. COMMERCIAL, MEDICARE, MEDICAID")
    policy_id: str = Field(description="Reference ID for the coverage policy")
    diagnosis: DiagnosisInfo = Field(description="Diagnosis details related to the requested service")
    requested_service: ServiceInfo = Field(description="Requested clinical procedure or drug details")
    clinical_summary: str = Field(description="Brief summary of clinical justification")
    supporting_document_ids: List[str] = Field(default_factory=list, description="IDs of documents attached to the claim")
    created_at: str = Field(description="Claim creation timestamp (ISO format)")
