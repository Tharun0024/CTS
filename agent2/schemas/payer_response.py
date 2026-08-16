from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class PayerResponse(BaseModel):
    """Response from Agent 1 (Payer Decision Engine).
    
    Encapsulates the payer's coverage decision and any supporting information
    needed for Agent 2 recovery routing logic.
    
    Decision outcomes align with Agent 1's DecisionOutcome:
    - APPROVED: Coverage approved, terminal (Agent 2 does nothing)
    - REJECTED: Coverage rejected; check is_recoverable flag
    - REQUEST_MORE_INFORMATION: Payer requests additional evidence for evaluation
    - HUMAN_REVIEW: Escalated to human review, terminal (Agent 2 does nothing)
    """
    submission_id: str = Field(description="Reference matching the original submission package ID")
    decision: Literal["APPROVED", "REJECTED", "REQUEST_MORE_INFORMATION", "HUMAN_REVIEW"] = Field(
        description="The coverage decision from the payer (Agent 1)"
    )
    reason: str = Field(description="Clinical reason or administrative notes from the payer")
    is_recoverable: bool = Field(
        default=True,
        description="For REJECTED: True if failure is due to missing evidence that can be recovered; "
                    "False if failure is due to clinical ineligibility (terminal). "
                    "Ignored for other decision types."
    )
    failed_criteria: List[str] = Field(
        default_factory=list,
        description="List of criterion IDs that failed or were unmet"
    )
    requested_information: List[str] = Field(
        default_factory=list,
        description="Specific descriptions of clinical records requested if decision is REQUEST_MORE_INFORMATION"
    )

