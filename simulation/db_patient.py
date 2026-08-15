"""
Big Patient Database Module (13 Historical Clinical Tables)
"""
import sqlite3
import os

CREATE_PATIENT_TABLES = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dob TEXT NOT NULL,
    gender TEXT NOT NULL,
    address TEXT,
    insurance_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS encounters (
    encounter_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    encounter_type TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    reason TEXT,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS conditions (
    condition_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    icd10_code TEXT NOT NULL,
    condition_name TEXT NOT NULL,
    onset_date TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    code TEXT NOT NULL,
    description TEXT NOT NULL,
    value TEXT NOT NULL,
    unit TEXT,
    observation_date TEXT NOT NULL,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS procedures (
    procedure_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    cpt_code TEXT NOT NULL,
    description TEXT NOT NULL,
    procedure_date TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS medications (
    medication_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    rxnorm_code TEXT,
    name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS allergies (
    allergy_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    substance TEXT NOT NULL,
    reaction TEXT,
    severity TEXT,
    onset_date TEXT,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS diagnostic_reports (
    report_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    report_type TEXT NOT NULL,
    findings TEXT NOT NULL,
    report_date TEXT NOT NULL,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS clinical_documents (
    document_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS care_plans (
    care_plan_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    title TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    source_record_id TEXT,
    document_id TEXT,
    evidence_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    content_reference TEXT NOT NULL,
    provenance TEXT NOT NULL,
    is_submitted INTEGER DEFAULT 1,
    kl_grade INTEGER,
    pt_weeks_completed INTEGER,
    neurological_deficit INTEGER,
    abnormal_stress_test INTEGER,
    refractory_angina INTEGER,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY(document_id) REFERENCES clinical_documents(document_id)
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    payer_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    requested_procedure TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS claim_submissions (
    submission_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    submission_date TEXT NOT NULL,
    submitted_evidence_ids TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY(claim_id) REFERENCES claims(claim_id)
);
"""


def init_patient_db(db_path: str) -> sqlite3.Connection:
    """Initialize the 13 Big Patient DB tables in SQLite."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(CREATE_PATIENT_TABLES)
    conn.commit()
    return conn


def get_patient_db_tables(db_path: str) -> list:
    """Return list of table names in Big Patient DB."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables
