from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import importlib

# Explicit evidence_type → semantic required_evidence_key map.
# Unknown types stay on evidence_id (unresolved) and fail closed downstream.
EVIDENCE_TYPE_KEY_MAP: Dict[str, str] = {
    "DIAGNOSIS": "diagnosis",
    "IMAGING": "imaging",
    "RECOMMENDATION": "recommendation",
    "CONSERVATIVE_TREATMENT": "conservative_treatment",
}

# Explicit payer naming aliases (never silent claim-payer override).
PAYER_NAME_ALIASES: Dict[str, str] = {
    "athena": "Aetna",
    "aetna": "Aetna",
    "cms": "CMS",
    "medicare": "CMS",
    "cms medicare": "CMS",
}


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

    def _resolve_sim_ids(self, patient_id: Optional[str], claim_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
        real_patient_id = patient_id
        real_claim_id = claim_id
        
        if patient_id and "-SIM-" in patient_id:
            parts = patient_id.split("-")
            try:
                seq = int(parts[-1])
            except ValueError:
                seq = 1
                
            sqlite3 = importlib.import_module("sqlite3")
            conn = sqlite3.connect(self.provider_db)
            try:
                cur = conn.execute("SELECT claim_id, patient_id, scenario_type FROM claims ORDER BY claim_id")
                claims_rows = cur.fetchall()
            finally:
                conn.close()
                self._cleanup_sqlite_module()
                
            scenario = ("COMPLETE", "MISSING_EVIDENCE", "NOT_SATISFIED")[(seq - 1) % 3]
            
            complete_claims = [r for r in claims_rows if r[2] == "COMPLETE"]
            omitted_claims = [r for r in claims_rows if r[2] == "EVIDENCE_OMITTED"]
            
            if scenario == "COMPLETE" and complete_claims:
                row = complete_claims[(seq - 1) % len(complete_claims)]
            elif scenario == "MISSING_EVIDENCE" and omitted_claims:
                row = omitted_claims[(seq - 1) % len(omitted_claims)]
            else:
                row = complete_claims[(seq - 1) % len(complete_claims)] if complete_claims else claims_rows[(seq - 1) % len(claims_rows)]
                
            real_claim_id = row[0]
            real_patient_id = row[1]
            
        return real_patient_id, real_claim_id

    @staticmethod
    def normalize_payer_alias(payer_name: Optional[str]) -> Optional[str]:
        """Resolve known payer naming aliases without inventing a payer."""
        if payer_name is None:
            return None
        raw = str(payer_name).strip()
        if not raw:
            return None
        return PAYER_NAME_ALIASES.get(raw.lower(), raw)

    @staticmethod
    def map_evidence_key(evidence_type: Optional[str], evidence_id: str) -> str:
        """Map known evidence_type values to semantic keys; otherwise keep evidence_id."""
        if not evidence_type:
            return evidence_id
        mapped = EVIDENCE_TYPE_KEY_MAP.get(str(evidence_type).strip().upper())
        return mapped if mapped else evidence_id

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

        patient_id_orig = patient_id
        claim_id_orig = claim_id

        # Resolve simulation IDs
        real_patient_id, real_claim_id = self._resolve_sim_ids(patient_id, claim_id)

        patient_row = self._fetch_one(
            self.provider_db,
            "SELECT patient_id, age, gender, birth_date, first_name, last_name, address, city, state, zip FROM patients WHERE patient_id = ?",
            (real_patient_id,),
        )
        if patient_row is None:
            return None

        if real_claim_id:
            claim_row = self._fetch_one(
                self.provider_db,
                "SELECT claim_id, patient_id, payer, policy_id, procedure_code, procedure_description, created_at, scenario_type FROM claims WHERE patient_id = ? AND claim_id = ? ORDER BY created_at DESC LIMIT 1",
                (real_patient_id, real_claim_id),
            )
        else:
            claim_row = self._fetch_one(
                self.provider_db,
                "SELECT claim_id, patient_id, payer, policy_id, procedure_code, procedure_description, created_at, scenario_type FROM claims WHERE patient_id = ? ORDER BY created_at DESC LIMIT 1",
                (real_patient_id,),
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
            evidence_id = row["evidence_id"]
            evidence_type = row["evidence_type"]
            evidence_item = {
                "evidence_key": self.map_evidence_key(evidence_type, evidence_id),
                "evidence_id": evidence_id,
                "source": row["source_type"],
                "status": "verified" if (row["sensitivity"] or "ROUTINE") == "ROUTINE" else "unverified",
                "confidence_score": 0.96,
                "is_ambiguous": False,
                "extracted_facts": {
                    "evidence_type": evidence_type,
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
        # Claim-relevant diagnoses only: ICD codes extracted from submitted evidence.
        # Do not dump the patient's full longitudinal condition history into the RAG query.
        diagnoses: List[str] = []
        for item in evidence_list:
            facts = item.get("extracted_facts") or {}
            content = facts.get("content_reference") if isinstance(facts, dict) else None
            for code in self._extract_diagnosis_codes(content):
                if code not in diagnoses:
                    diagnoses.append(code)

        procedures: List[str] = []
        procedure_code = (claim_row["procedure_code"] or "").strip()
        if procedure_code:
            procedures.append(procedure_code)

        clinical_metrics: Dict[str, Any] = {
            "patient_gender": patient_row["gender"],
            "patient_name": f"{patient_row['first_name']} {patient_row['last_name']}",
            "patient_dob": patient_row["birth_date"],
            "patient_address": f"{patient_row['address']}, {patient_row['city']}, {patient_row['state']} {patient_row['zip']}",
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

        claim_id_ret = claim_id_orig if claim_id_orig else (f"CLM-{patient_id_orig}" if patient_id_orig.startswith("SIM-") else claim_id)

        return {
            "claim_id": claim_id_ret,
            "submission": {
                "attempt": selected_attempt,
                "date": submission_row["timestamp"],
            },
            "case_data": {
                "case_id": claim_id_ret,
                "patient_age": patient_age,
                "diagnoses": diagnoses,
                "procedures": procedures,
                "clinical_metrics": clinical_metrics,
            },
            "evidence": evidence_list,
        }

    def get_provider_evidence_pool(self, patient_id: Optional[str]) -> List[Dict[str, Any]]:
        """Full provider-side evidence pool for one patient (Agent 2 recovery source).

        Reads ONLY the provider database (big_patient_data.db). Agent 2 recovery
        must never touch payer-side data; the payer database is intentionally not
        accessed here. Items use the same canonical evidence shape as
        get_provider_canonical_claim so recovered records can be appended to a
        resubmission claim without transformation.
        """
        if not patient_id:
            return []

        real_patient_id, _ = self._resolve_sim_ids(patient_id)

        rows = self._fetch_all(
            self.provider_db,
            "SELECT evidence_id, patient_id, source_type, source_record_id, document_id, evidence_type, event_date, content_reference, provenance, sensitivity FROM evidence WHERE patient_id = ? ORDER BY evidence_id",
            (real_patient_id,),
        )

        pool: List[Dict[str, Any]] = []
        for row in rows:
            evidence_id = row["evidence_id"]
            evidence_type = row["evidence_type"]
            pool.append(
                {
                    "evidence_key": self.map_evidence_key(evidence_type, evidence_id),
                    "evidence_id": evidence_id,
                    "source": row["source_type"],
                    "status": "verified" if (row["sensitivity"] or "ROUTINE") == "ROUTINE" else "unverified",
                    "confidence_score": 0.96,
                    "is_ambiguous": False,
                    "extracted_facts": {
                        "evidence_type": evidence_type,
                        "source_record_id": row["source_record_id"],
                        "event_date": row["event_date"],
                        "provenance": row["provenance"],
                        "sensitivity": row["sensitivity"],
                        "content_reference": row["content_reference"],
                    },
                    "unstructured_text": row["content_reference"],
                }
            )
        return pool

    def attach_payer_context(
        self,
        provider_claim: Dict[str, Any],
        payer_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Attach payer linkage into clinical_metrics without overriding claim_payer.

        patient_id → member_id linkage is preserved by ID equality. Naming aliases
        (e.g. Athena→Aetna) are recorded explicitly; claim_payer is never overwritten.
        """
        if provider_claim is None:
            raise ValueError("provider_claim cannot be None")

        claim = {
            "claim_id": provider_claim.get("claim_id"),
            "submission": dict(provider_claim.get("submission") or {}),
            "case_data": {
                **dict(provider_claim.get("case_data") or {}),
                "clinical_metrics": dict(
                    (provider_claim.get("case_data") or {}).get("clinical_metrics") or {}
                ),
            },
            "evidence": list(provider_claim.get("evidence") or []),
        }
        metrics = claim["case_data"]["clinical_metrics"]
        claim_payer = metrics.get("claim_payer")
        claim_payer_normalized = self.normalize_payer_alias(claim_payer)

        if payer_context is None:
            metrics["member_id"] = None
            metrics["member_payer_id"] = None
            metrics["plan_id"] = None
            metrics["coverage_status"] = None
            metrics["eligibility_eligible"] = None
            metrics["claim_payer_normalized"] = claim_payer_normalized
            metrics["member_payer_normalized"] = None
            metrics["claim_member_payer_mismatch"] = None
            metrics["payer_alias_notes"] = []
            claim["payer_context"] = None
            return claim

        member_payer = payer_context.get("payer_id")
        member_payer_normalized = self.normalize_payer_alias(member_payer)
        alias_notes: List[str] = []
        if claim_payer and claim_payer_normalized and claim_payer != claim_payer_normalized:
            alias_notes.append(
                f"claim_payer alias resolved: '{claim_payer}' → '{claim_payer_normalized}'"
            )
        if member_payer and member_payer_normalized and member_payer != member_payer_normalized:
            alias_notes.append(
                f"member_payer alias resolved: '{member_payer}' → '{member_payer_normalized}'"
            )

        mismatch = None
        if claim_payer_normalized is not None and member_payer_normalized is not None:
            mismatch = claim_payer_normalized != member_payer_normalized

        metrics["member_id"] = payer_context.get("member_id")
        metrics["member_payer_id"] = member_payer
        metrics["plan_id"] = payer_context.get("plan_id")
        coverage = payer_context.get("coverage") or {}
        metrics["coverage_status"] = coverage.get("status")
        eligibility = payer_context.get("eligibility") or {}
        metrics["eligibility_eligible"] = eligibility.get("eligible")
        metrics["claim_payer_normalized"] = claim_payer_normalized
        metrics["member_payer_normalized"] = member_payer_normalized
        metrics["claim_member_payer_mismatch"] = mismatch
        metrics["payer_alias_notes"] = alias_notes
        # claim_payer / claim_policy_id remain the authoritative claim fields.
        claim["payer_context"] = payer_context
        return claim

    def get_linked_runtime_claim(
        self,
        patient_id: Optional[str],
        claim_id: Optional[str] = None,
        attempt: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Provider claim + payer context via patient_id → member_id linkage."""
        provider_claim = self.get_provider_canonical_claim(patient_id, claim_id, attempt)
        if provider_claim is None:
            return None
        # Linkage rule: member_id == patient_id
        payer_context = self.get_payer_context(patient_id)
        return self.attach_payer_context(provider_claim, payer_context)

    def get_payer_context(self, member_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not member_id:
            return None

        member_id_orig = member_id
        real_member_id, _ = self._resolve_sim_ids(member_id)

        member_row = self._fetch_one(
            self.payer_db,
            "SELECT member_id, payer_id, plan_id, coverage_status, coverage_start, coverage_end, plan_product FROM members WHERE member_id = ?",
            (real_member_id,),
        )
        if member_row is None:
            return None

        eligibility_row = self._fetch_one(
            self.payer_db,
            "SELECT eligibility_id, member_id, is_eligible, effective_date, termination_date FROM eligibility WHERE member_id = ? ORDER BY effective_date DESC LIMIT 1",
            (real_member_id,),
        )

        benefits = self._fetch_all(
            self.payer_db,
            "SELECT benefit_id, plan_id, benefit_category, authorization_requirement, limits_units, frequency_limits FROM benefits WHERE plan_id = ? ORDER BY benefit_category",
            (member_row["plan_id"],),
        )

        utilization = self._fetch_all(
            self.payer_db,
            "SELECT utilization_id, member_id, metric_name, metric_value, updated_at FROM utilization WHERE member_id = ? ORDER BY updated_at DESC",
            (real_member_id,),
        )

        prior_authorizations = self._fetch_all(
            self.payer_db,
            "SELECT authorization_id, member_id, requested_service, diagnosis_code, provider, authorization_status, request_date, decision_date FROM prior_authorizations WHERE member_id = ? ORDER BY request_date DESC",
            (real_member_id,),
        )

        payer_claims = self._fetch_all(
            self.payer_db,
            "SELECT claim_id, member_id, service_date, provider_facility, claim_type, procedure_code, diagnosis_code, claim_status, allowed_amount, paid_amount, denial_reason FROM payer_claims WHERE member_id = ? ORDER BY service_date DESC",
            (real_member_id,),
        )

        eligibility = {
            "eligible": bool(eligibility_row["is_eligible"]) if eligibility_row is not None else None,
            "effective_date": eligibility_row["effective_date"] if eligibility_row is not None else None,
            "termination_date": eligibility_row["termination_date"] if eligibility_row is not None else None,
        }

        return {
            "member_id": member_id_orig,
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
