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

import hashlib
from typing import Any, Dict, List, Optional

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
        patient_id = f"PAT-{simulation_id}-{seq:04d}"
        claim_id = f"CLM-{patient_id}"
        scenario = self.scenario_for(seq)
        unit = _deterministic_unit(simulation_id, patient_id, "demo")
        age = 40 + int(unit * 40)  # 40..79 (below the age-exclusion band)
        gender = _GENDERS[seq % len(_GENDERS)]

        diagnosis = _sim_evidence(
            "diagnosis",
            f"EV-{patient_id}-DX",
            {
                "content_reference": f"Simulated diagnosis {'; '.join(self.diagnosis_codes)} for {patient_id}.",
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
            # Conservative-treatment documentation is absent at submission but
            # exists provider-side, so Agent2 recovery may find it.
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

        metrics: Dict[str, Any] = {
            "patient_gender": gender,
            "claim_scenario_type": scenario,
            "claim_payer": self.payer,
        }
        if self.policy_id:
            metrics["claim_policy_id"] = self.policy_id
        metrics.update(metrics_extra)

        canonical_claim = {
            "claim_id": claim_id,
            "patient_id": patient_id,
            "submission": {"attempt": 1, "date": "2026-08-16T00:00:00Z"},
            "case_data": {
                "case_id": claim_id,
                "patient_age": age,
                "diagnoses": list(self.diagnosis_codes),
                "procedures": [self.procedure_code],
                "clinical_metrics": metrics,
            },
            "evidence": claim_evidence,
        }

        # Insurer-side context: generated alongside but kept SEPARATE from
        # provider data; the pipeline and recovery pool never receive it.
        payer_context = {
            "member_id": f"MEM-{simulation_id}-{seq:04d}",
            "patient_id": patient_id,
            "payer_id": self.payer,
            "plan_id": f"PLAN-{self.payer.upper()}-SIM",
            "coverage_status": "ACTIVE",
            "policy_id": self.policy_id,
        }

        return {
            "patient_id": patient_id,
            "claim_id": claim_id,
            "age": age,
            "gender": gender,
            "scenario": scenario,
            "canonical_claim": canonical_claim,
            "provider_evidence_pool": provider_pool,
            "payer_context": payer_context,
        }
