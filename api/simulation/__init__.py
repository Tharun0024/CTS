"""Simulation + document ingestion API boundary (Phase 5B).

Simulation Manager over the EXISTING V1 claim/pipeline service: unique
patients, one-at-a-time processing, duration-based pacing, lifecycle
(start/stop/reset/delete/re-simulate) and document ingestion with
provenance. No second pipeline: every patient runs through the real Phase 5A
ClaimService and services/integrated_pipeline.
"""

from .document_ingest import build_document_evidence, extract_document_text
from .generator import SCENARIOS, DefaultPatientFactory
from .manager import (
    PatientNotFound,
    SimulatedProviderStore,
    SimulationBusy,
    SimulationManager,
    SimulationNotFound,
)
from .router import build_simulation_router, create_simulation_app
from .schemas import ReSimulateRequest, StartSimulationRequest

__all__ = [
    "SCENARIOS",
    "DefaultPatientFactory",
    "SimulatedProviderStore",
    "SimulationManager",
    "SimulationNotFound",
    "SimulationBusy",
    "PatientNotFound",
    "build_simulation_router",
    "create_simulation_app",
    "StartSimulationRequest",
    "ReSimulateRequest",
    "extract_document_text",
    "build_document_evidence",
]
