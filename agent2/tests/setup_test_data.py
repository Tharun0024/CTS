import sqlite3
import json
from datetime import datetime
from database.db_manager import get_db_connection

def seed_test_patients():
    print("Seeding test patients into SQLite clinical database...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # -------------------------------------------------------------
    # TEST-PATIENT-A: Approved Scenario (Repatha)
    # Fully meets all criteria (Age, Diagnosis, 120d Statin, LDL >= 100, Cardiologist)
    # -------------------------------------------------------------
    cursor.execute("INSERT OR REPLACE INTO patients VALUES ('TEST-PATIENT-A', 'Scenario A: Approved Patient', '1970-05-15', 'male', '123 Main St, Boston, MA 02111');")
    cursor.execute("INSERT OR REPLACE INTO conditions VALUES ('COND-A-01', 'TEST-PATIENT-A', '166110001', 'http://snomed.info/sct', 'Hyperlipidemia (disorder)', '2024-01-10T12:00:00Z', 'active');")
    cursor.execute("INSERT OR REPLACE INTO medications VALUES ('MED-A-01', 'TEST-PATIENT-A', '312961', 'http://www.nlm.nih.gov/research/umls/rxnorm', 'Simvastatin 20 MG Oral Tablet [Statin Trial: 120 days completed]', '2025-06-01T09:00:00Z', 'active', 'Dr. Primary Care');")
    cursor.execute("INSERT OR REPLACE INTO observations VALUES ('OBS-A-01', 'TEST-PATIENT-A', '18262-6', 'http://loinc.org', 'Low Density Lipoprotein Cholesterol [LDL-C] = 135 mg/dL', 135.0, 'mg/dL', '2026-08-01T08:00:00Z');")
    cursor.execute("INSERT OR REPLACE INTO encounters VALUES ('ENC-A-01', 'TEST-PATIENT-A', '385627008', 'http://snomed.info/sct', 'Cardiology Consult with Dr. Heart', '2026-07-15T14:30:00Z', 'finished');")

    # -------------------------------------------------------------
    # TEST-PATIENT-B: More Info Scenario (Repatha)
    # Meets all criteria, but LDL observation is withheld in V1, recovered in V2
    # -------------------------------------------------------------
    cursor.execute("INSERT OR REPLACE INTO patients VALUES ('TEST-PATIENT-B', 'Scenario B: More Info Patient', '1965-09-20', 'female', '456 Oak Ave, Worcester, MA 01609');")
    cursor.execute("INSERT OR REPLACE INTO conditions VALUES ('COND-B-01', 'TEST-PATIENT-B', '166110001', 'http://snomed.info/sct', 'Hyperlipidemia (disorder)', '2023-04-15T11:00:00Z', 'active');")
    cursor.execute("INSERT OR REPLACE INTO medications VALUES ('MED-B-01', 'TEST-PATIENT-B', '312961', 'http://www.nlm.nih.gov/research/umls/rxnorm', 'Simvastatin 20 MG Oral Tablet [Statin Trial: 120 days completed]', '2025-08-01T10:00:00Z', 'active', 'Dr. Clinic');")
    cursor.execute("INSERT OR REPLACE INTO observations VALUES ('OBS-B-01', 'TEST-PATIENT-B', '18262-6', 'http://loinc.org', 'Low Density Lipoprotein Cholesterol [LDL-C] = 145 mg/dL', 145.0, 'mg/dL', '2026-08-02T08:00:00Z');")
    cursor.execute("INSERT OR REPLACE INTO encounters VALUES ('ENC-B-01', 'TEST-PATIENT-B', '385627008', 'http://snomed.info/sct', 'Cardiology consult with Dr. Heart', '2026-07-20T10:00:00Z', 'finished');")

    # -------------------------------------------------------------
    # TEST-PATIENT-C: Rejected Scenario (Repatha)
    # Meets all criteria, but Simvastatin history is withheld in V1, recovered in V2
    # -------------------------------------------------------------
    cursor.execute("INSERT OR REPLACE INTO patients VALUES ('TEST-PATIENT-C', 'Scenario C: Rejection Recovery Patient', '1975-12-12', 'male', '789 Pine Rd, Springfield, MA 01103');")
    cursor.execute("INSERT OR REPLACE INTO conditions VALUES ('COND-C-01', 'TEST-PATIENT-C', '166110001', 'http://snomed.info/sct', 'Hyperlipidemia (disorder)', '2024-06-18T10:30:00Z', 'active');")
    cursor.execute("INSERT OR REPLACE INTO medications VALUES ('MED-C-01', 'TEST-PATIENT-C', '312961', 'http://www.nlm.nih.gov/research/umls/rxnorm', 'Simvastatin 20 MG Oral Tablet [Statin Trial: 120 days completed]', '2025-05-15T09:00:00Z', 'active', 'Dr. Hospital');")
    cursor.execute("INSERT OR REPLACE INTO observations VALUES ('OBS-C-01', 'TEST-PATIENT-C', '18262-6', 'http://loinc.org', 'Low Density Lipoprotein Cholesterol [LDL-C] = 110 mg/dL', 110.0, 'mg/dL', '2026-08-03T09:00:00Z');")
    cursor.execute("INSERT OR REPLACE INTO encounters VALUES ('ENC-C-01', 'TEST-PATIENT-C', '385627008', 'http://snomed.info/sct', 'Cardiology Consult with Dr. Heart', '2026-07-25T11:00:00Z', 'finished');")

    # -------------------------------------------------------------
    # TEST-PATIENT-D: Missing Evidence (Humulin)
    # Metformin step-therapy trial is completely missing. Escalates to HUMAN_REVIEW.
    # -------------------------------------------------------------
    cursor.execute("INSERT OR REPLACE INTO patients VALUES ('TEST-PATIENT-D', 'Scenario D: Missing Evidence Patient', '1980-02-28', 'female', '321 Elm Rd, Cambridge, MA 02138');")
    cursor.execute("INSERT OR REPLACE INTO conditions VALUES ('COND-D-01', 'TEST-PATIENT-D', '44054006', 'http://snomed.info/sct', 'Diabetes mellitus type 2 (disorder)', '2025-01-10T12:00:00Z', 'active');")
    # NO medications! (Missing Metformin!)
    cursor.execute("INSERT OR REPLACE INTO observations VALUES ('OBS-D-01', 'TEST-PATIENT-D', '4548-4', 'http://loinc.org', 'Hemoglobin A1c [HbA1c] = 8.5%', 8.5, '%', '2026-08-01T08:00:00Z');")

    # -------------------------------------------------------------
    # TEST-PATIENT-E: Uncertain/Short Evidence (Repatha)
    # Has a statin medication record but the duration is either short (10 days)
    # or duration is undocumented (Scenario E). Escalates to HUMAN_REVIEW.
    # -------------------------------------------------------------
    cursor.execute("INSERT OR REPLACE INTO patients VALUES ('TEST-PATIENT-E', 'Scenario E: Uncertain/Short Patient', '1978-07-04', 'male', '654 Cedar Ln, Newton, MA 02458');")
    cursor.execute("INSERT OR REPLACE INTO conditions VALUES ('COND-E-01', 'TEST-PATIENT-E', '166110001', 'http://snomed.info/sct', 'Hyperlipidemia (disorder)', '2024-03-22T09:00:00Z', 'active');")
    # Statin duration is either 10 days or completely undocumented. We use "statin trial duration undocumented"
    cursor.execute("INSERT OR REPLACE INTO medications VALUES ('MED-E-01', 'TEST-PATIENT-E', '312961', 'http://www.nlm.nih.gov/research/umls/rxnorm', 'Simvastatin 20 MG Oral Tablet [Statin Trial: duration undocumented]', '2025-10-01T08:00:00Z', 'active', 'Dr. Clinic');")
    cursor.execute("INSERT OR REPLACE INTO observations VALUES ('OBS-E-01', 'TEST-PATIENT-E', '18262-6', 'http://loinc.org', 'Low Density Lipoprotein Cholesterol [LDL-C] = 120 mg/dL', 120.0, 'mg/dL', '2026-08-04T08:00:00Z');")
    cursor.execute("INSERT OR REPLACE INTO encounters VALUES ('ENC-E-01', 'TEST-PATIENT-E', '385627008', 'http://snomed.info/sct', 'Cardiology consult with Dr. Heart', '2026-07-28T14:00:00Z', 'finished');")

    conn.commit()
    conn.close()
    print("Test patients successfully seeded!")

if __name__ == "__main__":
    seed_test_patients()
