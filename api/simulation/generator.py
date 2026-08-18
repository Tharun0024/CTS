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

# Scenario mix mirrors the DATA-VERSION1 scenario families (SC02..SC06):
#   COMPLETE          - full documentation, criteria satisfied
#   MISSING_EVIDENCE  - a required evidence item is absent at submission but
#                       exists in the provider pool (Agent2 may recover it)
#   NOT_SATISFIED     - documentation present but the clinical rule fails
SCENARIOS = ("COMPLETE", "MISSING_EVIDENCE", "NOT_SATISFIED")

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

    def scenario_for(self, seq: int) -> str:
        return SCENARIOS[(seq - 1) % len(SCENARIOS)]

    def make_patient(self, simulation_id: str, seq: int) -> Dict[str, Any]:
        scenario = self.scenario_for(seq)
        
        # 1. Sourcing unique IDs following the test contract
        patient_id = f"PAT-{simulation_id}-{seq:04d}"
        claim_id = f"CLM-{patient_id}"
        
        # 2. Sourcing real claim and patient details from the database
        from adapters.runtime_adapter import RuntimeAdapter
        adapter = RuntimeAdapter()
        claims_rows = adapter._fetch_all(
            adapter.provider_db,
            "SELECT claim_id, patient_id, scenario_type FROM claims ORDER BY claim_id"
        )
        
        complete_claims = [r for r in claims_rows if r["scenario_type"] == "COMPLETE"]
        omitted_claims = [r for r in claims_rows if r["scenario_type"] == "EVIDENCE_OMITTED"]
        
        if scenario == "COMPLETE" and complete_claims:
            row = complete_claims[(seq - 1) % len(complete_claims)]
        elif scenario == "MISSING_EVIDENCE" and omitted_claims:
            row = omitted_claims[(seq - 1) % len(omitted_claims)]
        else:
            # Fallback/NOT_SATISFIED or missing lists: pick any other complete claim
            row = complete_claims[(seq - 1) % len(complete_claims)] if complete_claims else claims_rows[(seq - 1) % len(claims_rows)]
            
        real_claim_id = row["claim_id"]
        real_patient_id = row["patient_id"]
        
        # 3. Retrieve authoritative persistent data using the unique simulated IDs
        canonical_claim = adapter.get_provider_canonical_claim(patient_id, claim_id)
        provider_pool = adapter.get_provider_evidence_pool(patient_id)
        payer_context = adapter.get_payer_context(patient_id)
        
        # For Agent 2 recovery pool, recover only items NOT already in the submitted claim
        submitted_evidence_ids = {ev.get("evidence_id") for ev in canonical_claim.get("evidence", []) if isinstance(ev, dict)}
        provider_pool = [item for item in provider_pool if item.get("evidence_id") not in submitted_evidence_ids]
        
        # Ensure scenario mapping on the claim record matches simulation scenario type
        metrics = canonical_claim["case_data"]["clinical_metrics"]
        metrics["claim_scenario_type"] = scenario
        
        case_data = canonical_claim["case_data"]
        age = case_data.get("patient_age") or 0
        gender = metrics.get("patient_gender") or "Unknown"
        name = metrics.get("patient_name") or f"Patient {real_patient_id}"
        dob = metrics.get("patient_dob") or "Unknown"
        address = metrics.get("patient_address") or "Unknown"
        
        return {
            "patient_id": patient_id,
            "claim_id": claim_id,
            "age": age,
            "gender": gender,
            "name": name,
            "dob": dob,
            "address": address,
            "contact": "Not on record",
            "relationship": "Not on record",
            "policy_holder": "Not on record",
            "scenario": scenario,
            "canonical_claim": canonical_claim,
            "provider_evidence_pool": provider_pool,
            "payer_context": payer_context,
        }
