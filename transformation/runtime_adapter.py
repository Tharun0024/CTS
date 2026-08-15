from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import importlib


class RuntimeAdapter:
    """Read Version-1 provider and payer data and normalize it for Agent 1.

    The adapter is intentionally upstream-only: it never inserts raw database rows into
    DecisionAgent, and it keeps payer context separate from clinical evidence.
    """

    def __init__(
        self,
        provider_db: Optional[str | Path] = None,
        payer_db: Optional[str | Path] = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.provider_db = str(provider_db or base_dir / "DATA-VERSION1" / "big_patient_data.db")
        self.payer_db = str(payer_db or base_dir / "DATA-VERSION1" / "payer_data.db")

    @staticmethod
    def _json_list(value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return [value]
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
            return [str(parsed)]
        return [str(value)]

    @staticmethod
    def _extract_diagnosis_codes(value: Any) -> List[str]:
        codes: List[str] = []
        if isinstance(value, str):
            for match in re.findall(r"\b(?:[A-Z]\d{2,3}(?:\.\d+)?)\b", value):
                if match not in codes:
                    codes.append(match)
            if not codes:
                for match in re.findall(r"\b[A-Z]\d{2,3}\.\d+\b", value):
                    if match not in codes:
                        codes.append(match)
        return codes

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _connect(self, database_path: str):
        sqlite3 = importlib.import_module("sqlite3")
        return sqlite3.connect(database_path)

    @staticmethod
    def _cleanup_sqlite_module() -> None:
        sys.modules.pop("sqlite3", None)

    def _fetch_one(self, database_path: str, query: str, params: Sequence[Any] = ()):
        conn = self._connect(database_path)
        try:
            sqlite3 = importlib.import_module("sqlite3")
            conn.row_factory = sqlite3.Row
            cur = conn.execute(query, params)
            row = cur.fetchone()
            return row
        finally:
            conn.close()
            self._cleanup_sqlite_module()

    def _fetch_all(self, database_path: str, query: str, params: Sequence[Any] = ()):
        conn = self._connect(database_path)
        try:
            sqlite3 = importlib.import_module("sqlite3")
            conn.row_factory = sqlite3.Row
            cur = conn.execute(query, params)
            return cur.fetchall()
        finally:
            conn.close()
            self._cleanup_sqlite_module()

    def get_provider_canonical_claim(
        self,
        patient_id: Optional[str],
        claim_id: Optional[str] = None,
        attempt: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        if not patient_id:
            return None

        patient_row = self._fetch_one(
            self.provider_db,
            "SELECT patient_id, age, gender FROM patients WHERE patient_id = ?",
            (patient_id,),
        )
        if patient_row is None:
            return None

        if claim_id:
            claim_row = self._fetch_one(
                self.provider_db,
                "SELECT claim_id, patient_id, payer, policy_id, procedure_code, procedure_description, created_at, scenario_type FROM claims WHERE patient_id = ? AND claim_id = ? ORDER BY created_at DESC LIMIT 1",
                (patient_id, claim_id),
            )
        else:
            claim_row = self._fetch_one(
                self.provider_db,
                "SELECT claim_id, patient_id, payer, policy_id, procedure_code, procedure_description, created_at, scenario_type FROM claims WHERE patient_id = ? ORDER BY created_at DESC LIMIT 1",
                (patient_id,),
            )

        if claim_row is None:
            return None

        claim_id = claim_row["claim_id"]
        submission_query = (
            "SELECT submission_id, claim_id, attempt, submitted_evidence_ids, timestamp, status "
            "FROM claim_submissions WHERE claim_id = ?"
        )
        submission_params: Tuple[Any, ...] = (claim_id,)
        if attempt is not None:
            submission_query += " AND attempt = ?"
            submission_params = (claim_id, attempt)
        submission_query += " ORDER BY attempt DESC, timestamp DESC LIMIT 1"

        submission_row = self._fetch_one(self.provider_db, submission_query, submission_params)
        if submission_row is None:
            return None

        selected_attempt = self._coerce_int(submission_row["attempt"])
        if selected_attempt is None:
            return None

        evidence_ids = self._json_list(submission_row["submitted_evidence_ids"])
        evidence_rows = self._fetch_all(
            self.provider_db,
            "SELECT evidence_id, patient_id, source_type, source_record_id, document_id, evidence_type, event_date, content_reference, provenance, sensitivity FROM evidence WHERE patient_id = ? AND evidence_id IN ({}) ORDER BY evidence_id".format(", ".join("?" for _ in evidence_ids)),
            (patient_id, *evidence_ids),
        ) if evidence_ids else []

        evidence_list: List[Dict[str, Any]] = []
        for row in evidence_rows:
            evidence_item = {
                "evidence_key": row["evidence_id"],
                "evidence_id": row["evidence_id"],
                "source": row["source_type"],
                "status": "verified" if (row["sensitivity"] or "ROUTINE") == "ROUTINE" else "unverified",
                "confidence_score": 0.96,
                "is_ambiguous": False,
                "extracted_facts": {
                    "evidence_type": row["evidence_type"],
                    "source_record_id": row["source_record_id"],
                    "event_date": row["event_date"],
                    "provenance": row["provenance"],
                    "sensitivity": row["sensitivity"],
                    "content_reference": row["content_reference"],
                },
                "unstructured_text": row["content_reference"],
            }
            evidence_list.append(evidence_item)

        patient_age = patient_row["age"]
        diagnoses: List[str] = []
        for row in self._fetch_all(
            self.provider_db,
            "SELECT diagnosis_code, diagnosis_description FROM conditions WHERE patient_id = ? ORDER BY condition_id",
            (patient_id,),
        ):
            code = (row["diagnosis_code"] or "").strip()
            if code and code not in diagnoses:
                diagnoses.append(code)
        for row in self._fetch_all(
            self.provider_db,
            "SELECT DISTINCT evidence_id, content_reference FROM evidence WHERE patient_id = ? ORDER BY evidence_id",
            (patient_id,),
        ):
            for code in self._extract_diagnosis_codes(row["content_reference"]):
                if code not in diagnoses:
                    diagnoses.append(code)

        procedures: List[str] = []
        procedure_code = (claim_row["procedure_code"] or "").strip()
        if procedure_code:
            procedures.append(procedure_code)

        clinical_metrics: Dict[str, Any] = {
            "patient_gender": patient_row["gender"],
            "claim_scenario_type": claim_row["scenario_type"],
            "claim_payer": claim_row["payer"],
            "claim_policy_id": claim_row["policy_id"],
        }

        if evidence_list:
            for item in evidence_list:
                facts = item.get("extracted_facts") or {}
                if isinstance(facts, dict):
                    for key, value in facts.items():
                        if key not in clinical_metrics:
                            clinical_metrics[key] = value

        return {
            "claim_id": claim_id,
            "submission": {
                "attempt": selected_attempt,
                "date": submission_row["timestamp"],
            },
            "case_data": {
                "case_id": claim_id,
                "patient_age": patient_age,
                "diagnoses": diagnoses,
                "procedures": procedures,
                "clinical_metrics": clinical_metrics,
            },
            "evidence": evidence_list,
        }

    def get_payer_context(self, member_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not member_id:
            return None

        member_row = self._fetch_one(
            self.payer_db,
            "SELECT member_id, payer_id, plan_id, coverage_status, coverage_start, coverage_end, plan_product FROM members WHERE member_id = ?",
            (member_id,),
        )
        if member_row is None:
            return None

        eligibility_row = self._fetch_one(
            self.payer_db,
            "SELECT eligibility_id, member_id, is_eligible, effective_date, termination_date FROM eligibility WHERE member_id = ? ORDER BY effective_date DESC LIMIT 1",
            (member_id,),
        )

        benefits = self._fetch_all(
            self.payer_db,
            "SELECT benefit_id, plan_id, benefit_category, authorization_requirement, limits_units, frequency_limits FROM benefits WHERE plan_id = ? ORDER BY benefit_category",
            (member_row["plan_id"],),
        )

        utilization = self._fetch_all(
            self.payer_db,
            "SELECT utilization_id, member_id, metric_name, metric_value, updated_at FROM utilization WHERE member_id = ? ORDER BY updated_at DESC",
            (member_id,),
        )

        prior_authorizations = self._fetch_all(
            self.payer_db,
            "SELECT authorization_id, member_id, requested_service, diagnosis_code, provider, authorization_status, request_date, decision_date FROM prior_authorizations WHERE member_id = ? ORDER BY request_date DESC",
            (member_id,),
        )

        payer_claims = self._fetch_all(
            self.payer_db,
            "SELECT claim_id, member_id, service_date, provider_facility, claim_type, procedure_code, diagnosis_code, claim_status, allowed_amount, paid_amount, denial_reason FROM payer_claims WHERE member_id = ? ORDER BY service_date DESC",
            (member_id,),
        )

        eligibility = {
            "eligible": bool(eligibility_row["is_eligible"]) if eligibility_row is not None else None,
            "effective_date": eligibility_row["effective_date"] if eligibility_row is not None else None,
            "termination_date": eligibility_row["termination_date"] if eligibility_row is not None else None,
        }

        return {
            "member_id": member_row["member_id"],
            "payer_id": member_row["payer_id"],
            "plan_id": member_row["plan_id"],
            "coverage": {
                "status": member_row["coverage_status"],
                "eligible": eligibility["eligible"],
                "coverage_start": member_row["coverage_start"],
                "coverage_end": member_row["coverage_end"],
            },
            "eligibility": eligibility,
            "benefits": [
                {
                    "benefit_id": row["benefit_id"],
                    "benefit_category": row["benefit_category"],
                    "authorization_requirement": bool(row["authorization_requirement"]),
                    "limits_units": row["limits_units"],
                    "frequency_limits": row["frequency_limits"],
                }
                for row in benefits
            ],
            "utilization": [
                {
                    "utilization_id": row["utilization_id"],
                    "metric_name": row["metric_name"],
                    "metric_value": row["metric_value"],
                    "updated_at": row["updated_at"],
                }
                for row in utilization
            ],
            "prior_authorizations": [
                {
                    "authorization_id": row["authorization_id"],
                    "requested_service": row["requested_service"],
                    "diagnosis_code": row["diagnosis_code"],
                    "provider": row["provider"],
                    "authorization_status": row["authorization_status"],
                    "request_date": row["request_date"],
                    "decision_date": row["decision_date"],
                }
                for row in prior_authorizations
            ],
            "claims": [
                {
                    "claim_id": row["claim_id"],
                    "service_date": row["service_date"],
                    "provider_facility": row["provider_facility"],
                    "claim_type": row["claim_type"],
                    "procedure_code": row["procedure_code"],
                    "diagnosis_code": row["diagnosis_code"],
                    "claim_status": row["claim_status"],
                    "allowed_amount": row["allowed_amount"],
                    "paid_amount": row["paid_amount"],
                    "denial_reason": row["denial_reason"],
                }
                for row in payer_claims
            ],
        }
