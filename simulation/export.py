"""
Export Module: Generates DATA-VERSION1/ Deliverable Artifacts with Full Resubmission Persistence
"""
import os
import csv
import sqlite3
from typing import List
from simulation.db_patient import init_patient_db
from simulation.db_payer import init_payer_db
from simulation.scenarios import generate_8_scenarios, ClinicalScenario
from simulation.resubmissions import create_resubmission_sequence


def export_deliverables(output_dir: str = "DATA-VERSION1"):
    """
    Build and export all CTS V1 deliverables to DATA-VERSION1/ including persisted resubmission history.
    """
    os.makedirs(output_dir, exist_ok=True)
    patient_db_path = os.path.join(output_dir, "big_patient_data.db")
    payer_db_path = os.path.join(output_dir, "payer_data.db")
    csv_path = os.path.join(output_dir, "clinical_events_PA_ids.csv")
    excel_path = os.path.join(output_dir, "final_patient_data_PA_ids_final.xlsx")
    scenarios_md_path = os.path.join(output_dir, "SCENARIOS.md")

    # Remove existing files if present to ensure clean rebuild
    for p in [patient_db_path, payer_db_path]:
        if os.path.exists(p):
            os.remove(p)

    # 1. Initialize SQLite Databases
    patient_conn = init_patient_db(patient_db_path)
    payer_conn = init_payer_db(payer_db_path)
    
    scenarios = generate_8_scenarios()
    
    patient_cursor = patient_conn.cursor()
    payer_cursor = payer_conn.cursor()

    csv_rows = [["patient_id", "member_id", "payer_id", "event_type", "event_date", "cpt_code", "details"]]

    # Populate DBs and CSV data for the 8 primary scenarios
    for sc in scenarios:
        # Insert Patient
        patient_cursor.execute(
            "INSERT OR REPLACE INTO patients VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sc.patient_id, f"Patient {sc.patient_id}", "1980-01-01", "F", "123 Main St", sc.payer_linkage.member_id, "2026-01-01T00:00:00")
        )
        
        # Insert Encounter
        patient_cursor.execute(
            "INSERT OR REPLACE INTO encounters VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"ENC_{sc.patient_id}", sc.patient_id, "Specialist Consultation", "PRV_101", "2026-06-01T10:00:00", "2026-06-01T11:00:00", "Prior auth evaluation")
        )
        
        # Insert Payer Member
        coverage_stat = "ACTIVE" if not sc.payer_linkage.is_mismatch_scenario and sc.payer_linkage.payer_id != "UNKNOWN_PAYER_INC" else "INACTIVE"
        payer_cursor.execute(
            "INSERT OR REPLACE INTO members VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sc.payer_linkage.member_id, sc.patient_id, sc.payer_linkage.payer_id, sc.payer_linkage.plan_id, coverage_stat, "2026-01-01", "2026-12-31", "COMMERCIAL_PPO")
        )
        
        # Insert Payer Eligibility
        is_elig = 1 if coverage_stat == "ACTIVE" else 0
        payer_cursor.execute(
            "INSERT OR REPLACE INTO eligibility VALUES (?, ?, ?, ?, ?)",
            (f"ELIG_{sc.patient_id}", sc.payer_linkage.member_id, is_elig, "2026-01-01", "2026-12-31")
        )

        # Insert Claim in Big Patient DB
        cpt_str = ",".join(sc.cpt_codes)
        claim_id = f"CLM_{sc.patient_id}"
        patient_cursor.execute(
            "INSERT OR REPLACE INTO claims VALUES (?, ?, ?, ?, ?, ?, ?)",
            (claim_id, sc.patient_id, sc.payer_linkage.payer_id, sc.payer_linkage.plan_id, cpt_str, sc.expected_decision, "2026-07-01T09:00:00")
        )

        # Insert Payer Claim in Payer DB
        payer_cursor.execute(
            "INSERT OR REPLACE INTO payer_claims VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (claim_id, sc.payer_linkage.member_id, "2026-07-01", "ST_JUDE_CLINIC", "PROFESSIONAL", cpt_str, "M17.11", sc.expected_decision, 1500.00, 0.00, "None" if sc.expected_decision == "APPROVE" else "Policy criteria evaluation")
        )
        
        # Insert Primary Submission
        sub_ev_ids = ",".join([e.evidence_id for e in sc.submitted_evidence])
        patient_cursor.execute(
            "INSERT OR REPLACE INTO claim_submissions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"SUB_{sc.patient_id}_1", claim_id, 1, "2026-07-01T09:00:00", sub_ev_ids, sc.expected_decision, sc.description)
        )

        # Insert Evidence (both available and submitted) including structured clinical metrics
        for ev in sc.available_evidence:
            neuro_int = 1 if ev.neurological_deficit is True else (0 if ev.neurological_deficit is False else None)
            stress_int = 1 if ev.abnormal_stress_test is True else (0 if ev.abnormal_stress_test is False else None)
            angina_int = 1 if ev.refractory_angina is True else (0 if ev.refractory_angina is False else None)
            patient_cursor.execute(
                "INSERT OR REPLACE INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ev.evidence_id, ev.patient_id, ev.source_record_id, ev.document_id, ev.evidence_type, ev.event_date, ev.content_reference, ev.provenance, 1 if ev.is_submitted else 0, ev.kl_grade, ev.pt_weeks_completed, neuro_int, stress_int, angina_int)
            )
            csv_rows.append([
                sc.patient_id,
                sc.payer_linkage.member_id,
                sc.payer_linkage.payer_id,
                ev.evidence_type,
                ev.event_date,
                cpt_str,
                ev.content_reference
            ])

    # 2. Persist Resubmission Sequence (Scenario 3 - PA003) into claim_submissions and evidence tables
    scenario_3 = [s for s in scenarios if s.scenario_id == 3][0]
    resub_sequence = create_resubmission_sequence(scenario_3)
    
    # Insert resubmitted claim record if distinct
    resub_claim_id = resub_sequence[0].claim_id
    patient_cursor.execute(
        "INSERT OR REPLACE INTO claims VALUES (?, ?, ?, ?, ?, ?, ?)",
        (resub_claim_id, scenario_3.patient_id, scenario_3.payer_linkage.payer_id, scenario_3.payer_linkage.plan_id, "72148", "APPROVE", "2026-07-01T09:00:00")
    )
    
    # Insert Attempt 1 and Attempt 2 into claim_submissions table in SQLite
    for att in resub_sequence:
        sub_ids_str = ",".join(att.submitted_evidence_ids)
        patient_cursor.execute(
            "INSERT OR REPLACE INTO claim_submissions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (att.submission_id, att.claim_id, att.attempt_number, att.submission_date, sub_ids_str, att.outcome, att.notes)
        )
        
        # Persist any newly attached evidence from resubmission attempts
        for ev in att.submitted_evidence:
            neuro_int = 1 if ev.neurological_deficit is True else (0 if ev.neurological_deficit is False else None)
            stress_int = 1 if ev.abnormal_stress_test is True else (0 if ev.abnormal_stress_test is False else None)
            angina_int = 1 if ev.refractory_angina is True else (0 if ev.refractory_angina is False else None)
            patient_cursor.execute(
                "INSERT OR REPLACE INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ev.evidence_id, ev.patient_id, ev.source_record_id, ev.document_id, ev.evidence_type, ev.event_date, ev.content_reference, ev.provenance, 1, ev.kl_grade, ev.pt_weeks_completed, neuro_int, stress_int, angina_int)
            )

    patient_conn.commit()
    payer_conn.commit()
    patient_conn.close()
    payer_conn.close()

    # 3. Export CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)

    # 4. Export Excel
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Patient Clinical Events"
        for row in csv_rows:
            ws.append(row)
        wb.save(excel_path)
    except ImportError:
        with open(excel_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerows(csv_rows)

    # 5. Export SCENARIOS.md
    with open(scenarios_md_path, "w", encoding="utf-8") as f:
        f.write("# CTS V1 Clinical Scenarios Documentation\n\n")
        f.write("| # | Scenario | Patient ID | Payer | Plan | Policy ID | Expected Result | Description |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for sc in scenarios:
            pol = sc.payer_linkage.policy_id or ("N/A (Intentional RAG Failure)" if sc.payer_linkage.policy_lookup_mode == "intentional_rag_failure" else "N/A (No Policy Established)")
            f.write(f"| {sc.scenario_id} | {sc.name} | {sc.patient_id} | {sc.payer_linkage.payer_id} | {sc.payer_linkage.plan_id} | {pol} | `{sc.expected_decision}` | {sc.description} |\n")
        f.write("\n\n## Resubmission Handling\n")
        f.write("Scenario 3 (PA003) supports multi-attempt resubmissions persisted in `big_patient_data.db`:\n")
        f.write("- **Attempt 1 (`SUB_CLM_RESUB_PA003_ATT1`)**: Missing physical therapy documentation -> `REQUEST_MORE_INFORMATION`\n")
        f.write("- **Attempt 2 (`SUB_CLM_RESUB_PA003_ATT2`)**: Provider attaches missing 6-week PT report (`EV_RESUB_PA003_PT`) under same claim ID (`CLM_RESUB_PA003`) -> `APPROVE`\n")

    print(f"Export completed successfully to {output_dir}/")


if __name__ == "__main__":
    export_deliverables()
