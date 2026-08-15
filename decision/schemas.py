from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator, field_validator


class EvidenceStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CONTRADICTORY = "contradictory"


class DecisionOutcome(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_MORE_INFORMATION = "REQUEST_MORE_INFORMATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class CriterionAssessmentStatus(str, Enum):
    """Permitted LLM assessment states for one RAG policy criterion."""
    SATISFIED = "SATISFIED"
    NOT_SATISFIED = "NOT_SATISFIED"
    MISSING = "MISSING"
    UNCERTAIN = "UNCERTAIN"
    CONFLICTING = "CONFLICTING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Rule(BaseModel):
    """
    Represents a rule check against a dictionary or an object field.
    Allows comparing patient metrics, diagnoses, or evidence facts.
    """
    field: str  # Path to the field, e.g. "patient_age", "clinical_metrics.HbA1c", "diagnoses"
    operator: str  # operators: "eq", "ne", "lt", "lte", "gt", "gte", "contains", "not_contains", "in", "not_in"
    value: Any


class PolicyExclusion(BaseModel):
    """
    Conditions under which a claim/case is immediately rejected.
    """
    exclusion_id: str
    name: str
    rule: Rule
    required_evidence_keys: List[str] = Field(default_factory=list)  # Supporting evidence keys for the exclusion


class PolicyCriterion(BaseModel):
    """
    Criteria required to approve a claim/case.
    """
    criterion_id: str
    name: str
    description: str
    mandatory: bool = True
    applicability_rule: Optional[Rule] = None  # Rule to check if this criterion applies to the case
    required_evidence_keys: List[str] = Field(default_factory=list)
    # RAG-policy metadata used only by the criterion-reasoning contract.
    # ``required_evidence`` is normalized into the legacy deterministic key list.
    interpretation_guidance: str = ""
    required_evidence: List[str] = Field(default_factory=list)
    evaluation_type: str = ""
    clinical_rule: Optional[Rule] = None  # Checked against CaseData
    evidence_rule: Optional[Rule] = None  # Checked against EvidenceItem extracted_facts

    @model_validator(mode="after")
    def normalize_required_evidence(self) -> "PolicyCriterion":
        if self.required_evidence and not self.required_evidence_keys:
            self.required_evidence_keys = list(self.required_evidence)
        elif self.required_evidence_keys and not self.required_evidence:
            self.required_evidence = list(self.required_evidence_keys)
        return self


class Policy(BaseModel):
    """
    A policy is a group of exclusions and criteria used for determination.
    """
    policy_id: str
    name: str
    exclusions: List[PolicyExclusion] = Field(default_factory=list)
    criteria: List[PolicyCriterion] = Field(default_factory=list)


class CaseData(BaseModel):
    """
    Patient and claim clinical metrics.
    """
    case_id: str
    patient_age: int
    diagnoses: List[str] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    clinical_metrics: Dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    """
    Represents a piece of clinical evidence.
    """
    evidence_key: str  # Map to PolicyCriterion/Exclusion required_evidence_keys
    evidence_id: Optional[str] = None  # Unique evidence identifier
    source: str  # E.g. "Lab Report", "Physician Notes", "Claims Database"
    status: EvidenceStatus
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    is_ambiguous: bool = False
    extracted_facts: Dict[str, Any] = Field(default_factory=dict)
    unstructured_text: Optional[str] = None


class CanonicalClaim(BaseModel):
    """The only claim input accepted by the criterion-assessment contract."""
    model_config = {"extra": "forbid"}

    case_data: CaseData
    evidence: List[EvidenceItem] = Field(default_factory=list)


class CriterionAssessment(BaseModel):
    """A constrained, explainable LLM assessment of exactly one policy criterion."""
    model_config = {"extra": "forbid"}

    criterion_id: str = Field(..., min_length=1)
    status: CriterionAssessmentStatus
    evidence_paths: List[str] = Field(default_factory=list)
    # For MISSING only: names the policy-defined required-evidence expectation,
    # never a claimed canonical-data path.
    required_evidence_paths: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)

    @field_validator("reasoning", mode="before")
    @classmethod
    def convert_reasoning_to_list(cls, v: Any) -> Any:
        if isinstance(v, str):
            lines = []
            for line in v.replace("\r", "").split("\n"):
                cleaned = line.strip()
                if cleaned.startswith("- ") or cleaned.startswith("* "):
                    cleaned = cleaned[2:].strip()
                if cleaned:
                    lines.append(cleaned)
            if not lines:
                lines = [v]
            return lines
        return v


class EvidenceProvenance(BaseModel):
    """
    Details of what specific evidence item supported or failed a criterion evaluation.
    """
    evidence_key: str
    evidence_id: Optional[str] = None
    source: str
    relevant_fact: Any
    confidence_score: float
    evaluation_status: str  # status of this specific evidence (e.g. verified, low_confidence, contradictory, ambiguous, unverified)
    criterion_id: str


class CriterionEvaluation(BaseModel):
    """
    Detailed output evaluation for a single policy criterion.
    """
    criterion_id: str
    state: str  # "PASS", "FAIL", "MISSING", "CONFLICTING", "NOT_APPLICABLE"
    evidence_provenance: List[EvidenceProvenance] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)


class DecisionResponse(BaseModel):
    """
    The output decision returned by the decision agent.
    """
    case_id: str
    outcome: DecisionOutcome
    reasoning: List[str] = Field(default_factory=list)
    exclusion_results: Dict[str, bool] = Field(default_factory=dict)  # exclusion_id -> met/triggered
    criteria_results: Dict[str, bool] = Field(default_factory=dict)   # criterion_id -> is_clean_satisfied
    criteria_evaluations: Dict[str, CriterionEvaluation] = Field(default_factory=dict)  # criterion_id -> Detail
    evidence_status: Dict[str, str] = Field(default_factory=dict)     # evidence_key -> status or error
    criterion_assessments: Dict[str, CriterionAssessment] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)  # Any execution/parsing exceptions encountered
    claim_id: Optional[str] = None
    policy_id: Optional[str] = None
    submission_attempt: Optional[int] = None
