from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class PolicyCriterion(BaseModel):
    criterion_id: str = Field(description="Stable criterion key (e.g. C01, C02)")
    description: str = Field(description="Normalized requirement text (e.g. age limits, step-therapy trial, lab thresholds)")
    required: bool = Field(default=True, description="True if this is a mandatory condition")
    source: str = Field(description="The source of the policy, e.g. CMS, AETNA")
    policy_reference: str = Field(description="Policy ID and section info, e.g. CPB-001 Sec 3")

class CriterionEvaluation(BaseModel):
    criterion_id: str = Field(description="Reference to the evaluated criterion_id")
    criterion_description: str = Field(description="The evaluated criterion rule description")
    status: Literal["SATISFIED", "NOT_SATISFIED", "UNCERTAIN"] = Field(description="Rule satisfaction status")
    patient_evidence_ids: List[str] = Field(default_factory=list, description="IDs of patient evidence supporting this decision (empty if not satisfied)")
    policy_evidence_id: Optional[str] = Field(default=None, description="ID of corresponding policy chunk or reference")
    explanation: str = Field(description="Detailed clinical justification/rationale for the status")
