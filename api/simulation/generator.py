"""Simulated patient generation (Phase 5B).

Generates unique simulated patients and their Version-1 canonical claims for
the Simulation Manager. Two hard separation rules:

  - PROVIDER-side data (demographics, canonical claim, recoverable evidence
    pool) is what the real V1 pipeline ever sees.
  - INSURER-side data (member/coverage context) is generated alongside but
    kept in a separate payload; the simulation manager stores it separately
    and it is NEVER fed into the pipeline or the recovery pool.

The generator never touches the real DATA-VERSION1 databases: simulated
patients exist only inside their simulation run.
"""

import os
import json
import yaml
import hashlib
from typing import Any, Dict, List, Optional


def _lookup_policy_details(policy_id: str) -> Optional[dict]:
    config_path = os.path.join("config", "config.yaml")
    if not os.path.exists(config_path):
        return None
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    normalized_path = config["paths"]["normalized_data"]
    if not os.path.exists(normalized_path):
        return None
    with open(normalized_path, "r", encoding="utf-8") as f:
        policies = json.load(f)
    for p in policies:
        if p.get("policy_id") == policy_id:
            return p
    for p in policies:
        if p.get("policy_id", "").lower() == policy_id.lower():
            return p
    return None


# Scenario mix mirrors the DATA-VERSION1 scenario families (SC02..SC06):
#   COMPLETE          - full documentation, criteria satisfied
#   MISSING_EVIDENCE  - a required evidence item is absent at submission but
#                       exists in the provider pool (Agent2 may recover it)
#   NOT_SATISFIED     - documentation present but the clinical rule fails
SCENARIOS = ("COMPLETE", "MISSING_EVIDENCE", "NOT_SATISFIED")

_GENDERS = ("Female", "Male")


def _deterministic_unit(simulation_id: str, patient_id: str, salt: str) -> float:
    """Stable pseudo-random float in [0, 1) derived from the run + patient ids."""
    digest = hashlib.sha256(f"{simulation_id}:{patient_id}:{salt}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 2**32


def _sim_evidence(
    evidence_key: str,
    evidence_id: str,
    facts: Dict[str, Any],
    provenance: str,
) -> Dict[str, Any]:
    """Canonical V1 evidence shape (same contract as RuntimeAdapter rows)."""
    extracted = dict(facts)
    extracted.setdefault("sensitivity", "ROUTINE")
    extracted.setdefault("provenance", provenance)
    return {
        "evidence_key": evidence_key,
        "evidence_id": evidence_id,
        "source": "Simulated Provider Record",
        "status": "verified",
        "confidence_score": 0.96,
        "is_ambiguous": False,
        "extracted_facts": extracted,
        "unstructured_text": extracted.get("content_reference"),
    }


class DefaultPatientFactory:
    """Deterministic per-run patient factory.

    ``make_patient(simulation_id, seq)`` returns a descriptor dict:
      patient_id / claim_id          unique ids bound to the run
      scenario                       one of SCENARIOS (cycles by seq)
      canonical_claim                provider-side V1 canonical claim
      provider_evidence_pool         extra provider-side recoverable evidence
      payer_context                  insurer-side context (kept separate)

    IDs embed the simulation_id (which is uuid-backed), so every run produces
    fresh unique patient ids and no id can collide across runs.
    """

    def __init__(
        self,
        policy_id: Optional[str] = None,
        payer: str = "Aetna",
        procedure_code: str = "27447",
        procedure: str = "Total Knee Arthroplasty",
        diagnosis_codes: Optional[List[str]] = None,
    ):
        self.policy_id = policy_id
        self.payer = payer
        self.procedure_code = procedure_code
        self.procedure = procedure
        self.diagnosis_codes = list(diagnosis_codes or ["M17.11"])

    def scenario_for(self, seq: int) -> str:
        return SCENARIOS[(seq - 1) % len(SCENARIOS)]

    def make_patient(self, simulation_id: str, seq: int) -> Dict[str, Any]:
        # 1. Resolve dynamic policy-payer-service pairing based on policy family
        policy_id = self.policy_id
        if not policy_id:
            # Alternate policy families (Aetna CPB vs CMS NCD/LCD)
            policy_id = "CPB-0660" if seq % 2 == 1 else "LCD-L36575"
            
        details = _lookup_policy_details(policy_id)
        if details:
            payer = details.get("payer") or "Aetna"
            procedure_code = details["procedure_codes"][0] if details.get("procedure_codes") else "27447"
            procedure = details.get("policy_title") or "Total Knee Arthroplasty"
            diag_codes = details.get("diagnosis_codes") or ["M17.11"]
        else:
            payer = "Aetna" if "CPB" in policy_id else "CMS (Medicare)"
            procedure_code = "27447"
            procedure = "Total Knee Arthroplasty"
            diag_codes = ["M17.11"]

        patient_id = f"PAT-{simulation_id}-{seq:04d}"
        claim_id = f"CLM-{patient_id}"
        scenario = self.scenario_for(seq)
        unit = _deterministic_unit(simulation_id, patient_id, "demo")
        age = 40 + int(unit * 40)  # 40..79
        gender = _GENDERS[seq % len(_GENDERS)]

        # 2. Generate complete, realistic patient demographics
        names_female = ["Sarah Jenkins", "Emily Rodriguez", "Jessica Chen", "Amanda Taylor", "Ashley Martinez"]
        names_male = ["David Miller", "Christopher Anderson", "Matthew Jackson", "Joshua White", "Daniel Harris"]
        name = names_female[seq % len(names_female)] if gender == "Female" else names_male[seq % len(names_male)]
        
        birth_year = 2026 - age
        month = 1 + int(unit * 11)
        day = 1 + int(unit * 27)
        dob = f"{birth_year:04d}-{month:02d}-{day:02d}"
        
        addresses = [
            "742 Evergreen Terrace, Springfield, OR 97477",
            "123 Maple Street, Bloomington, IN 47401",
            "456 Oakwood Drive, Columbus, OH 43215",
            "890 Pine Needle Lane, Ann Arbor, MI 48104",
            "567 Cedar Crest Road, Madison, WI 53703"
        ]
        address = addresses[seq % len(addresses)]
        phone = f"(555) {100 + seq:03d}-{2000 + seq:04d}"
        
        if seq % 5 == 0:
            relationship = "Spouse"
            policy_holder = names_male[(seq + 1) % len(names_male)] if gender == "Female" else names_female[(seq + 1) % len(names_female)]
        elif seq % 7 == 0:
            relationship = "Child"
            policy_holder = names_male[(seq + 2) % len(names_male)] if gender == "Female" else names_female[(seq + 2) % len(names_female)]
        else:
            relationship = "Self"
            policy_holder = name

        # 3. Create simulated evidence items
        diagnosis = _sim_evidence(
            "diagnosis",
            f"EV-{patient_id}-DX",
            {
                "content_reference": f"Simulated diagnosis {'; '.join(diag_codes)} for {patient_id}.",
                "source_record_id": f"COND-{patient_id}-01",
                "event_date": "2026-07-01",
            },
            provenance=f"SIM-PROVIDER:{simulation_id}:{patient_id}:conditions",
        )
        conservative = _sim_evidence(
            "conservative_treatment",
            f"EV-{patient_id}-PT",
            {
                "content_reference": f"Simulated 16 weeks of physical therapy for {patient_id}.",
                "pt_weeks_completed": 16,
                "source_record_id": f"ENC-{patient_id}-02",
                "event_date": "2026-07-10",
            },
            provenance=f"SIM-PROVIDER:{simulation_id}:{patient_id}:encounters",
        )
        imaging = _sim_evidence(
            "imaging",
            f"EV-{patient_id}-IMG",
            {
                "content_reference": f"Simulated knee radiograph, KL grade 4, for {patient_id}.",
                "kl_grade": 4,
                "source_record_id": f"RAD-{patient_id}-03",
                "event_date": "2026-07-15",
            },
            provenance=f"SIM-PROVIDER:{simulation_id}:{patient_id}:diagnostic_reports",
        )

        claim_evidence = [diagnosis]
        provider_pool: List[Dict[str, Any]] = []
        metrics_extra: Dict[str, Any] = {}
        if scenario == "COMPLETE":
            claim_evidence.extend([conservative, imaging])
        elif scenario == "MISSING_EVIDENCE":
            claim_evidence.append(imaging)
            provider_pool.append(conservative)
        else:  # NOT_SATISFIED
            short_pt = _sim_evidence(
                "conservative_treatment",
                f"EV-{patient_id}-PT",
                {
                    "content_reference": f"Simulated 2 weeks of physical therapy for {patient_id}.",
                    "pt_weeks_completed": 2,
                    "source_record_id": f"ENC-{patient_id}-02",
                    "event_date": "2026-07-10",
                },
                provenance=f"SIM-PROVIDER:{simulation_id}:{patient_id}:encounters",
            )
            claim_evidence.extend([short_pt, imaging])
            metrics_extra["claim_scenario_type"] = "NOT_SATISFIED"

        # 4. Enforce provider/insurer separation in clinical metrics
        metrics: Dict[str, Any] = {
            "patient_gender": gender,
            "patient_name": name,
            "patient_dob": dob,
            "patient_address": address,
            "patient_phone": phone,
            "patient_relationship": relationship,
            "policy_holder": policy_holder,
            "claim_scenario_type": scenario,
            "claim_payer": payer,
            "claim_policy_id": policy_id,
        }
        metrics.update(metrics_extra)

        canonical_claim = {
            "claim_id": claim_id,
            "patient_id": patient_id,
            "submission": {"attempt": 1, "date": "2026-08-16T00:00:00Z"},
            "case_data": {
                "case_id": claim_id,
                "patient_age": age,
                "diagnoses": list(diag_codes),
                "procedures": [procedure_code],
                "clinical_metrics": metrics,
            },
            "evidence": claim_evidence,
        }

        # Insurer-side context (kept SEPARATE from provider data)
        payer_context = {
            "member_id": f"MEM-{simulation_id}-{seq:04d}",
            "patient_id": patient_id,
            "payer_id": payer,
            "plan_id": f"PLAN-{payer.upper()}-SIM",
            "coverage_status": "ACTIVE",
            "policy_id": policy_id,
        }

        return {
            "patient_id": patient_id,
            "claim_id": claim_id,
            "age": age,
            "gender": gender,
            "name": name,
            "dob": dob,
            "address": address,
            "contact": phone,
            "relationship": relationship,
            "policy_holder": policy_holder,
            "scenario": scenario,
            "canonical_claim": canonical_claim,
            "provider_evidence_pool": provider_pool,
            "payer_context": payer_context,
        }

