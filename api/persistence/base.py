"""Abstract persistence/repository interfaces for the API boundary (Phase 5A).

The API service layer depends ONLY on these interfaces. The current
implementations are in-memory (default) and SQLite (wrapping the agent2
database). A cloud-storage backend can later replace either implementation
without touching workflow logic (services/integrated_pipeline.py) or the
control plane: everything stays repository-agnostic.

Repositories are deliberately minimal:
  - ClaimRecordRepository:      serialized claim records (status + decision +
                                versions + submissions + evidence request).
  - ProviderDecisionRepository: append-only provider ACCEPT/DECLINE history.
  - WorkflowEventRepository:    append-only workflow audit events (timeline).
  - SimulationRepository:       simulation run records (Phase 5B; each record
                                carries its patient -> claim relationships).

Append-only stores must never mutate or delete historical entries. The only
deletion permitted anywhere is simulation-scoped cleanup (Phase 5B): a
simulation may delete the claim records and simulation data IT owns, never
data belonging to other simulations or to the live claims API.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ClaimRecordRepository(ABC):
    """Stores serialized claim records keyed by claim_id.

    ``save`` is an upsert of the CURRENT record snapshot (latest state); the
    immutable version history lives INSIDE the record (``versions``), so
    historical claim versions are never overwritten.
    """

    @abstractmethod
    def save(self, record: Dict[str, Any]) -> None:
        """Insert or replace the current record snapshot for ``record["claim_id"]``."""

    @abstractmethod
    def get(self, claim_id: str) -> Optional[Dict[str, Any]]:
        """Return the stored record or None when unknown."""

    @abstractmethod
    def list(self) -> List[Dict[str, Any]]:
        """Return all stored records, newest ``updated_at`` first."""

    @abstractmethod
    def delete(self, claim_id: str) -> bool:
        """Remove one record; return True when it existed.

        Used exclusively by simulation-scoped cleanup (Phase 5B); the live
        claims API never deletes records.
        """


class ProviderDecisionRepository(ABC):
    """Append-only history of provider ACCEPT/DECLINE decisions."""

    @abstractmethod
    def save(self, decision: Dict[str, Any]) -> None:
        """Append one decision record; re-saving the same decision_id is a no-op."""

    @abstractmethod
    def get(self, claim_id: str) -> List[Dict[str, Any]]:
        """Return all decisions for a claim in recording order."""


class WorkflowEventRepository(ABC):
    """Append-only workflow audit events (the claim timeline)."""

    @abstractmethod
    def save(self, event: Dict[str, Any]) -> None:
        """Append one immutable workflow event."""

    @abstractmethod
    def get_events(self, claim_id: str) -> List[Dict[str, Any]]:
        """Return all events for a claim in chronological order."""


class SimulationRepository(ABC):
    """Simulation run records (Phase 5B).

    Each record is a snapshot of one simulation run and carries the
    simulation -> patient -> claim relationships (patient list with claim
    ids, per-patient timing, documents). Records are upserted while a run is
    active; ``delete`` removes a run's record during simulation-scoped
    cleanup and returns True when the record existed.
    """

    @abstractmethod
    def save(self, record: Dict[str, Any]) -> None:
        """Insert or replace the record for ``record["simulation_id"]``."""

    @abstractmethod
    def get(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Return the stored record or None when unknown."""

    @abstractmethod
    def list(self) -> List[Dict[str, Any]]:
        """Return all simulation records, newest ``created_at`` first."""

    @abstractmethod
    def delete(self, simulation_id: str) -> bool:
        """Remove one simulation record; return True when it existed."""
