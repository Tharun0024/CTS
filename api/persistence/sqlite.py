"""SQLite repository implementations (Phase 5A).

These persist through the agent2 SQLite database (agent2/database schema)
behind the abstract repository interfaces. The service layer never touches
SQLite directly, so a cloud-storage backend can replace this module later
without changing workflow logic.

All SQL is owned by this module (connections carry a generous busy timeout so
transient OS-level file locks - e.g. antivirus scans on temp directories -
never surface as "database is locked" during normal sequential use).

Tables used:
  - claim_records:      serialized claim record snapshots (added in Phase 5A)
  - provider_decisions: append-only provider ACCEPT/DECLINE history (Phase 4)
  - agent2_audit:       append-only workflow audit events (existing)
  - simulation_records: simulation run snapshots (added in Phase 5B)
"""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import (
    ClaimRecordRepository,
    ProviderDecisionRepository,
    SimulationRepository,
    WorkflowEventRepository,
)

# Sequential writers only; a long busy timeout absorbs transient file locks.
_BUSY_TIMEOUT_SECONDS = 30.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _SqliteStoreBase:
    """Shared connection management for the SQLite repositories."""

    def __init__(self):
        # Lazy imports: keep the SQLite option out of the default import path.
        from agent2.database.db_manager import init_db

        init_db()  # idempotent CREATE TABLE IF NOT EXISTS

    def _connect(self) -> sqlite3.Connection:
        # Resolve DB_PATH at call time so tests can relocate the database.
        from agent2.database.db_manager import DB_PATH

        conn = sqlite3.connect(DB_PATH, timeout=_BUSY_TIMEOUT_SECONDS)
        conn.row_factory = sqlite3.Row
        return conn


class SqliteClaimRecordRepository(ClaimRecordRepository, _SqliteStoreBase):
    def save(self, record: Dict[str, Any]) -> None:
        claim_id = record.get("claim_id")
        if not claim_id:
            raise ValueError("Claim record must carry a claim_id.")
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO claim_records
                    (claim_id, patient_id, status, record_json, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    claim_id,
                    record.get("patient_id"),
                    record.get("status"),
                    json.dumps(record, default=str),
                    record.get("updated_at"),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, claim_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT record_json FROM claim_records WHERE claim_id = ?;",
                (claim_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return json.loads(row["record_json"])

    def list(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT record_json FROM claim_records ORDER BY updated_at DESC;"
            ).fetchall()
        finally:
            conn.close()
        return [json.loads(row["record_json"]) for row in rows]

    def delete(self, claim_id: str) -> bool:
        # Simulation-scoped cleanup only (Phase 5B).
        conn = self._connect()
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.execute(
                "DELETE FROM claim_records WHERE claim_id = ?;", (claim_id,)
            )
            conn.execute(
                "DELETE FROM claims WHERE claim_id = ?;", (claim_id,)
            )
            conn.execute(
                "DELETE FROM agent2_audit WHERE claim_id = ?;", (claim_id,)
            )
            conn.execute(
                "DELETE FROM provider_decisions WHERE claim_id = ?;", (claim_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


class SqliteProviderDecisionRepository(ProviderDecisionRepository, _SqliteStoreBase):
    def save(self, decision: Dict[str, Any]) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO provider_decisions (
                    decision_id, claim_id, claim_version, decision, evidence_ids,
                    evidence_request_id, correlation_id, reason, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    decision["decision_id"],
                    decision["claim_id"],
                    int(decision.get("claim_version") or 1),
                    decision["decision"],
                    json.dumps(list(decision.get("evidence_ids") or [])),
                    decision.get("evidence_request_id"),
                    decision.get("correlation_id"),
                    decision.get("reason"),
                    decision.get("decided_at") or _utc_now_iso(),
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Idempotent re-save of the same immutable decision_id.
            conn.rollback()
        finally:
            conn.close()

    def get(self, claim_id: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM provider_decisions WHERE claim_id = ? ORDER BY decided_at ASC;",
                (claim_id,),
            ).fetchall()
        finally:
            conn.close()
        results = []
        for row in rows:
            item = dict(row)
            try:
                item["evidence_ids"] = json.loads(item.get("evidence_ids") or "[]")
            except (TypeError, ValueError):
                item["evidence_ids"] = []
            results.append(item)
        return results


class SqliteWorkflowEventRepository(WorkflowEventRepository, _SqliteStoreBase):
    def save(self, event: Dict[str, Any]) -> None:
        action = event.get("action") or ""
        if event.get("evidence_request_id"):
            action += f" [erq={event['evidence_request_id']}]"
        if event.get("detail"):
            action += f" | {event['detail']}"
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO agent2_audit (
                    audit_id, correlation_id, claim_id, claim_version,
                    state_before, state_after, action, timestamp, result, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event.get("audit_id") or f"AUD-API-{event.get('seq', 0)}",
                    event.get("correlation_id") or "",
                    event.get("claim_id") or "",
                    int(event.get("claim_version") or 1),
                    event.get("state_before") or "",
                    event.get("state_after") or "",
                    action,
                    _utc_now_iso(),
                    event.get("result"),
                    event.get("error"),
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Idempotent re-sync of an already-persisted immutable event.
            conn.rollback()
        finally:
            conn.close()

    def get_events(self, claim_id: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM agent2_audit WHERE claim_id = ? ORDER BY timestamp ASC;",
                (claim_id,),
            ).fetchall()
        finally:
            conn.close()
        return [dict(row) for row in rows]


class SqliteSimulationRepository(SimulationRepository, _SqliteStoreBase):
    def save(self, record: Dict[str, Any]) -> None:
        simulation_id = record.get("simulation_id")
        if not simulation_id:
            raise ValueError("Simulation record must carry a simulation_id.")
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO simulation_records
                    (simulation_id, status, record_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    simulation_id,
                    record.get("status"),
                    json.dumps(record, default=str),
                    record.get("created_at"),
                    record.get("updated_at") or _utc_now_iso(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT record_json FROM simulation_records WHERE simulation_id = ?;",
                (simulation_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return json.loads(row["record_json"])

    def list(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT record_json FROM simulation_records ORDER BY created_at DESC;"
            ).fetchall()
        finally:
            conn.close()
        return [json.loads(row["record_json"]) for row in rows]

    def delete(self, simulation_id: str) -> bool:
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM simulation_records WHERE simulation_id = ?;",
                (simulation_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
