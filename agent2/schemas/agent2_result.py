from pydantic import BaseModel, Field
from typing import List, Optional
from .policy import CriterionEvaluation
from .evidence import Evidence
from .submission import SubmissionPackage

class Agent2Result(BaseModel):
    agent2_run_id: str = Field(description="Unique ID for this specific orchestration run")
    claim_id: str = Field(description="Reference to the claim ID")
    version: int = Field(description="The claim version that was processed")
    status: str = Field(description="Final workflow state, e.g. APPROVED, HUMAN_REVIEW, BLOCKED, WAITING_FOR_PAYER")
    validation_status: str = Field(description="Validation result, e.g. VALID, INVALID")
    evidence_status: str = Field(description="Status of clinical evidence, e.g. FOUND, MISSING")
    policy_status: str = Field(description="Status of policy retrieval, e.g. RETRIEVED, NOT_FOUND")
    criterion_results: List[CriterionEvaluation] = Field(default_factory=list, description="Detailed evaluations of policy criteria")
    supporting_evidence: List[Evidence] = Field(default_factory=list, description="All retrieved evidence candidate records")
    missing_information: List[str] = Field(default_factory=list, description="Specific clinical descriptions determined to be missing")
    human_review_required: bool = Field(default=False, description="Whether the claim requires human intervention")
    submission_package: Optional[SubmissionPackage] = Field(default=None, description="The final package submitted, if any")
