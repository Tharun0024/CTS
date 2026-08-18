"""Pydantic request models for the simulation + document ingestion API (Phase 5B).

Responses are plain dicts built by the service layer (same convention as the
Phase 5A claims API) so the contract stays explicit and repository-agnostic.
"""

from typing import Optional

from pydantic import BaseModel, Field


class StartSimulationRequest(BaseModel):
    """Start a new simulation run.

    ``source`` mirrors the frontend contract (``POST /api/simulation/start``).
    ``count`` is the number of simulated patients; each patient is processed
    ONE AT A TIME through the real V1 pipeline and the measured end-to-end
    duration paces the next patient.
    """

    source: str = "CMS Medicare simulation scenario"
    count: Optional[int] = Field(default=None, ge=1, le=200)
    policy_id: Optional[str] = None  # default: first policy in the loaded RAG chunks
    provider_decision: str = "ACCEPT"
    max_resubmissions: Optional[int] = Field(default=None, ge=0)
    pause_seconds: float = Field(default=0.0, ge=0.0, le=3600.0)


class ReSimulateRequest(BaseModel):
    """Re-run an existing simulation configuration as a FRESH run."""

    count: Optional[int] = Field(default=None, ge=1, le=200)
