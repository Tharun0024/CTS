import sqlite3
import json
from datetime import datetime
from database.db_manager import get_db_connection
from schemas.policy import CriterionEvaluation

class ClaimRepository:
    def __init__(self):
        pass

    def create_claim(self, claim_id: str, patient_id: str, provider_id: str, payer_id: str, payer_type: str, policy_id: str, status: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        cursor.execute("""
        INSERT OR REPLACE INTO claims (claim_id, patient_id, provider_id, payer_id, payer_type, policy_id, current_version, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?);
        """, (claim_id, patient_id, provider_id, payer_id, payer_type, policy_id, status, now))
        conn.commit()
        conn.close()

    def get_claim(self, claim_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM claims WHERE claim_id = ?;", (claim_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_claim_version(self, claim_id: str, version: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM claim_versions WHERE claim_id = ? AND version = ?;", (claim_id, version))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_claim_version(self, claim_id: str, version: int, canonical_claim_json: str, status: str, previous_version: int = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        
        # 1. Insert into claim_versions
        cursor.execute("""
        INSERT OR REPLACE INTO claim_versions (claim_id, version, canonical_claim_json, status, created_at, previous_version)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (claim_id, version, canonical_claim_json, status, now, previous_version))
        
        # 2. Update claims table current_version and status
        cursor.execute("""
        UPDATE claims 
        SET current_version = ?, status = ?
        WHERE claim_id = ?;
        """, (version, status, claim_id))
        
        conn.commit()
        conn.close()

    def update_claim_status(self, claim_id: str, status: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE claims SET status = ? WHERE claim_id = ?;", (status, claim_id))
        conn.commit()
        conn.close()

    def save_submission(self, submission_id: str, claim_id: str, claim_version: int, status: str, attempt_number: int, idempotency_key: str, payer_response_json: str = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        cursor.execute("""
        INSERT OR REPLACE INTO submissions (submission_id, claim_id, claim_version, submitted_at, status, attempt_number, idempotency_key, payer_response_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (submission_id, claim_id, claim_version, now, status, attempt_number, idempotency_key, payer_response_json))
        conn.commit()
        conn.close()

    def get_submissions_for_claim(self, claim_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM submissions WHERE claim_id = ? ORDER BY submitted_at DESC;", (claim_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_criterion_results(self, claim_id: str, claim_version: int, results: list):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Clear older matches/results for this specific version if overwritten
        cursor.execute("DELETE FROM criterion_results WHERE claim_id = ? AND claim_version = ?;", (claim_id, claim_version))
        cursor.execute("DELETE FROM evidence_matches WHERE claim_id = ? AND claim_version = ?;", (claim_id, claim_version))
        
        now = datetime.utcnow().isoformat() + "Z"
        
        for res in results:
            evidence_str = ",".join(res.patient_evidence_ids)
            cursor.execute("""
            INSERT INTO criterion_results (claim_id, claim_version, criterion_id, status, evidence_ids, policy_reference, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (claim_id, claim_version, res.criterion_id, res.status, evidence_str, res.policy_evidence_id or "", res.explanation))
            
            # Populate evidence matches
            for ev_id in res.patient_evidence_ids:
                # We can deduce the match type from the evidence ID prefix or keep it default
                match_type = "LLM_SEMANTIC"
                confidence = 1.0 if res.status == "SATISFIED" else 0.5
                cursor.execute("""
                INSERT INTO evidence_matches (claim_id, claim_version, criterion_id, evidence_id, match_type, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (claim_id, claim_version, res.criterion_id, ev_id, match_type, confidence, now))
                
        conn.commit()
        conn.close()

    def get_criterion_results(self, claim_id: str, claim_version: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM criterion_results WHERE claim_id = ? AND claim_version = ?;", (claim_id, claim_version))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_evidence_matches(self, claim_id: str, claim_version: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence_matches WHERE claim_id = ? AND claim_version = ?;", (claim_id, claim_version))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def create_human_review(self, review_id: str, claim_id: str, reason: str, failed_criteria: list, missing_information: list, uncertain_information: list, recommended_action: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        
        failed_str = ",".join(failed_criteria)
        missing_str = json.dumps(missing_information)
        uncertain_str = json.dumps(uncertain_information)
        
        cursor.execute("""
        INSERT OR REPLACE INTO human_reviews (review_id, claim_id, reason, failed_criteria, missing_information, uncertain_information, recommended_action, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (review_id, claim_id, reason, failed_str, missing_str, uncertain_str, recommended_action, now))
        conn.commit()
        conn.close()

    def get_human_reviews(self, claim_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM human_reviews WHERE claim_id = ? ORDER BY created_at DESC;", (claim_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_claim_versions(self, claim_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM claim_versions WHERE claim_id = ? ORDER BY version ASC;", (claim_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
