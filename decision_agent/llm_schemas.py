from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from decision_agent.schemas import CriterionAssessment


class InterpretationState(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNCERTAIN = "UNCERTAIN"
    CONFLICTING = "CONFLICTING"
    MISSING = "MISSING"


class ExtractedFact(BaseModel):
    """
    Structured extraction of a single clinical/claim fact from evidence.
    """
    evidence_key: str
    evidence_id: Optional[str] = None
    source: str
    original_text: str  # Original relevant text/information
    extracted_fact: Dict[str, Any]  # Structured fact (e.g. {"hba1c": 8.5})
    confidence: float = Field(..., ge=0.0, le=1.0)
    state: InterpretationState
    interpretation_status: str  # Maps to "verified", "unverified", "contradictory", etc.
    reasoning: str


class CriterionInterpretation(BaseModel):
    """
    Relates the extracted facts and evidence interpretation to a policy criterion.
    """
    criterion_id: str
    state: InterpretationState
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradictory_evidence_ids: List[str] = Field(default_factory=list)
    uncertainty_details: Optional[str] = None
    is_ambiguous: bool = False
    missing_information_details: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning_summary: str


class LLMStructuredResponse(BaseModel):
    """
    The full structured payload returned by the LLM.
    """
    extracted_facts: List[ExtractedFact] = Field(default_factory=list)
    criterion_interpretations: List[CriterionInterpretation] = Field(default_factory=list)
    overall_reasoning_summary: str


class LLMCriterionAssessmentResponse(BaseModel):
    """Strict response contract for the canonical-claim/RAG-policy LLM step."""
    model_config = {"extra": "forbid"}

    criterion_assessments: List[CriterionAssessment]
