from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class PayerResponse(BaseModel):
    submission_id: str = Field(description="Reference matching the original submission package ID")
    decision: Literal["APPROVED", "REJECTED", "MORE_INFO"] = Field(description="The coverage decision from the payer (Agent 1)")
    reason: str = Field(description="Clinical reason or administrative notes from the payer")
    failed_criteria: List[str] = Field(default_factory=list, description="List of criterion IDs that failed or were unmet")
    requested_information: List[str] = Field(default_factory=list, description="Specific descriptions of clinical records requested if decision is MORE_INFO")
