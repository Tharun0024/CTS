from pydantic import BaseModel, Field
from typing import List

class HumanReview(BaseModel):
    review_id: str = Field(description="Unique human review tracking identifier")
    claim_id: str = Field(description="Reference to the claim ID")
    reason: str = Field(description="Primary rationale for escalation, e.g., missing evidence, ambiguous records")
    failed_criteria: List[str] = Field(default_factory=list, description="List of criterion IDs that failed evaluation")
    missing_information: List[str] = Field(default_factory=list, description="Details of necessary information that was not found")
    uncertain_information: List[str] = Field(default_factory=list, description="Details of ambiguous evidence needing human interpretation")
    recommended_action: str = Field(description="Recommended steps for the human reviewer (e.g. contact patient, query external lab)")
    created_at: str = Field(description="ISO timestamp of review request")
