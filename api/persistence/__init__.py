"""Persistence/repository interfaces + implementations for the API boundary.

Interfaces only are stable; implementations are swappable (in-memory today,
SQLite included, cloud storage later) without touching workflow logic.
"""

from .base import (
    ClaimRecordRepository,
    ProviderDecisionRepository,
    SimulationRepository,
    WorkflowEventRepository,
)
from .memory import (
    InMemoryClaimRecordRepository,
    InMemoryProviderDecisionRepository,
    InMemorySimulationRepository,
    InMemoryWorkflowEventRepository,
)

__all__ = [
    "ClaimRecordRepository",
    "ProviderDecisionRepository",
    "WorkflowEventRepository",
    "SimulationRepository",
    "InMemoryClaimRecordRepository",
    "InMemoryProviderDecisionRepository",
    "InMemoryWorkflowEventRepository",
    "InMemorySimulationRepository",
    # SQLite implementations are imported lazily by callers that opt in:
    #   from api.persistence.sqlite import SqliteClaimRecordRepository, ...
]
