"""In-memory repository implementations (Phase 5A).

Default stores for the API boundary: zero I/O, ideal for tests and for the
V1 single-process runtime. Semantics match the abstract contracts exactly:
claim records are upserted snapshots (history lives inside the record),
provider decisions and workflow events are append-only.
"""

from typing import Any, Dict, List, Optional

from .base import (
    ClaimRecordRepository,
    ProviderDecisionRepository,
    SimulationRepository,
    WorkflowEventRepository,
)


class InMemoryClaimRecordRepository(ClaimRecordRepository):
    def __init__(self):
        self._records: Dict[str, Dict[str, Any]] = {}

    def save(self, record: Dict[str, Any]) -> None:
        claim_id = record.get("claim_id")
        if not claim_id:
            raise ValueError("Claim record must carry a claim_id.")
        self._records[claim_id] = record

    def get(self, claim_id: str) -> Optional[Dict[str, Any]]:
        return self._records.get(claim_id)

    def list(self) -> List[Dict[str, Any]]:
        return sorted(
            self._records.values(),
            key=lambda r: str(r.get("updated_at") or ""),
            reverse=True,
        )

    def delete(self, claim_id: str) -> bool:
        # Simulation-scoped cleanup only (Phase 5B).
        return self._records.pop(claim_id, None) is not None


class InMemoryProviderDecisionRepository(ProviderDecisionRepository):
    def __init__(self):
        self._decisions: List[Dict[str, Any]] = []   # append-only

    def save(self, decision: Dict[str, Any]) -> None:
        decision_id = decision.get("decision_id")
        if any(existing.get("decision_id") == decision_id for existing in self._decisions):
            return  # idempotent re-save of the same immutable record
        self._decisions.append(decision)

    def get(self, claim_id: str) -> List[Dict[str, Any]]:
        return [d for d in self._decisions if d.get("claim_id") == claim_id]


class InMemoryWorkflowEventRepository(WorkflowEventRepository):
    def __init__(self):
        self._events: List[Dict[str, Any]] = []       # append-only

    def save(self, event: Dict[str, Any]) -> None:
        self._events.append(event)

    def get_events(self, claim_id: str) -> List[Dict[str, Any]]:
        return [e for e in self._events if e.get("claim_id") == claim_id]


class InMemorySimulationRepository(SimulationRepository):
    def __init__(self):
        self._records: Dict[str, Dict[str, Any]] = {}

    def save(self, record: Dict[str, Any]) -> None:
        simulation_id = record.get("simulation_id")
        if not simulation_id:
            raise ValueError("Simulation record must carry a simulation_id.")
        self._records[simulation_id] = record

    def get(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return self._records.get(simulation_id)

    def list(self) -> List[Dict[str, Any]]:
        return sorted(
            self._records.values(),
            key=lambda r: str(r.get("created_at") or ""),
            reverse=True,
        )

    def delete(self, simulation_id: str) -> bool:
        return self._records.pop(simulation_id, None) is not None
