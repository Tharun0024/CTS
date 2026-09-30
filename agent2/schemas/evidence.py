from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class EvidenceState(str, Enum):
    """State of evidence retrieval and evaluation.
    
    FOUND: Evidence successfully retrieved from provider database and parsed.
    MISSING: Evidence searched for but not found in provider database.
    """
    FOUND = "FOUND"
    MISSING = "MISSING"

class Evidence(BaseModel):
    evidence_id: str = Field(description="Unique identifier for this evidence (e.g. EV-OBS-123)")
    patient_id: str = Field(description="Reference to the patient ID")
    source_type: str = Field(description="Clinical source table, e.g., conditions, medications, observations, procedures, encounters, documents")
    source_record_id: str = Field(description="Primary key of the original database record")
    event_date: str = Field(description="Event timestamp or onset date")
    content: str = Field(description="Clinical description, dosage, value/unit, or code details")
    state: EvidenceState = Field(default=EvidenceState.FOUND, description="Retrieval state: FOUND or MISSING")
    relevance_score: float = Field(default=1.0, description="Calculated matching relevance")
    evidence_type: str = Field(description="High-level category: CLINICAL, DOCUMENT, LAB, PROCEDURE, MEDICATION, OBSERVATION")
    retrieved_at: str = Field(description="ISO timestamp of when the evidence was queried")

class PolicyEvidence(BaseModel):
    policy_id: str = Field(description="Policy reference identifier")
    policy_source: str = Field(description="Source of the policy, e.g. AETNA, CMS")
    section: str = Field(description="Policy section header or path")
    criterion_id: str = Field(description="The ID of the normalized criterion this evidence maps to")
    text: str = Field(description="The actual clinical rules text excerpted from the policy")
