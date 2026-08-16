import sqlite3
from datetime import datetime
from ..db_manager import get_db_connection

class AuditRepository:
    def __init__(self):
        pass

    def log_audit(self, audit_id: str, correlation_id: str, claim_id: str, claim_version: int, state_before: str, state_after: str, action: str, result: str = None, error: str = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        cursor.execute("""
        INSERT INTO agent2_audit (audit_id, correlation_id, claim_id, claim_version, state_before, state_after, action, timestamp, result, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (audit_id, correlation_id, claim_id, claim_version, state_before, state_after, action, now, result, error))
        conn.commit()
        conn.close()

    def get_audit_trail(self, claim_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agent2_audit WHERE claim_id = ? ORDER BY timestamp ASC;", (claim_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
