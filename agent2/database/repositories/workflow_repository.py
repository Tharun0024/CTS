import json
from typing import List, Optional

from ..db_manager import get_db_connection


class WorkflowRepository:
    """Persistence for workflow control-plane artifacts (Phase 4).

    Append-only by design: provider accept/decline decisions are INSERT-only
    history records and are never updated or deleted in place.
    """

    def record_provider_decision(
        self,
        decision_id: str,
        claim_id: str,
        claim_version: int,
        decision: str,
        evidence_ids: List[str],
        evidence_request_id: Optional[str],
        correlation_id: Optional[str],
        reason: Optional[str],
        decided_at: str,
    ):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO provider_decisions (
                decision_id, claim_id, claim_version, decision, evidence_ids,
                evidence_request_id, correlation_id, reason, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                decision_id,
                claim_id,
                claim_version,
                decision,
                json.dumps(list(evidence_ids or [])),
                evidence_request_id,
                correlation_id,
                reason,
                decided_at,
            ),
        )
        conn.commit()
        conn.close()

    def get_provider_decisions(self, claim_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM provider_decisions WHERE claim_id = ? ORDER BY decided_at ASC;",
            (claim_id,),
        )
        rows = cursor.fetchall()
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
