from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# ==========================================
# INPUT SCHEMAS
# ==========================================

class InsurancePrimary(BaseModel):
    payer: str = Field(..., description="Insurance payer name")
    policy_id: Optional[str] = Field(None, description="Optional insurance policy identifier")

class InsuranceInfo(BaseModel):
    primary: InsurancePrimary = Field(..., description="Primary insurance details")

class DiagnosisInfo(BaseModel):
    code: str = Field(..., description="ICD-10 diagnosis code")
    description: str = Field(..., description="Diagnosis clinical description")

class ProcedureInfo(BaseModel):
    code: str = Field(..., description="CPT procedure code")
    description: str = Field(..., description="Procedure clinical description")

class ClaimInput(BaseModel):
    claim_id: str = Field(..., description="Unique claim identifier")
    insurance: InsuranceInfo = Field(..., description="Claim insurance details")
    diagnosis: List[DiagnosisInfo] = Field(..., description="List of diagnoses codes and descriptions")
    procedure: ProcedureInfo = Field(..., description="CPT procedure code and description")
    clinical_domain: str = Field(..., description="Target clinical specialty/domain")


# ==========================================
# INTERNAL SCHEMAS
# ==========================================

class NormalizedChunk(BaseModel):
    chunk_id: str
    policy_id: str
    payer: str
    policy_title: str
    clinical_domain: str
    procedure_codes: List[str]
    diagnosis_codes: List[str]
    section: str
    criterion_id: str
    criterion_type: str
    criterion_name: str
    text: str
    documentation_requirements: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    contraindications: List[str] = Field(default_factory=list)
    source_reference: Dict[str, str] = Field(default_factory=dict)
    policy_status: str = "active"
    effective_date: Optional[str] = None
    revision_date: Optional[str] = None
    chunk_type: str = "general"


# ==========================================
# OUTPUT SCHEMAS
# ==========================================

class PolicyMatch(BaseModel):
    policy_id: str
    payer: str
    relevance_score: float

class CriterionSource(BaseModel):
    policy_id: str
    section: str

class Criterion(BaseModel):
    criterion_id: str
    criterion: str
    policy_requirement: str
    source: CriterionSource

class DocumentationRequirement(BaseModel):
    requirement: str
    source: str

class ClaimOutput(BaseModel):
    claim_id: str
    policy_matches: List[PolicyMatch] = Field(..., description="Matching policy details")
    criteria: List[Criterion] = Field(..., description="Extracted policy criteria items")
    documentation_requirements: List[DocumentationRequirement] = Field(..., description="Extracted clinical documentation requirements")
