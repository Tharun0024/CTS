"""
Payer Database Module: Preserves Exact Specified Payer DB Schemas
"""
import sqlite3
import os

CREATE_PAYER_TABLES = """
CREATE TABLE IF NOT EXISTS members (
    member_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    payer_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    coverage_status TEXT NOT NULL,
    coverage_start TEXT NOT NULL,
    coverage_end TEXT,
    plan_product TEXT
);

CREATE TABLE IF NOT EXISTS eligibility (
    eligibility_id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    is_eligible INTEGER NOT NULL,
    effective_date TEXT NOT NULL,
    termination_date TEXT,
    FOREIGN KEY(member_id) REFERENCES members(member_id)
);

CREATE TABLE IF NOT EXISTS payer_claims (
    claim_id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    service_date TEXT NOT NULL,
    provider_facility TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    procedure_code TEXT NOT NULL,
    diagnosis_code TEXT NOT NULL,
    claim_status TEXT NOT NULL,
    allowed_amount REAL,
    paid_amount REAL,
    denial_reason TEXT,
    FOREIGN KEY(member_id) REFERENCES members(member_id)
);

CREATE TABLE IF NOT EXISTS prior_authorizations (
    authorization_id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    requested_service TEXT NOT NULL,
    diagnosis_code TEXT NOT NULL,
    provider TEXT NOT NULL,
    authorization_status TEXT NOT NULL,
    request_date TEXT NOT NULL,
    decision_date TEXT,
    FOREIGN KEY(member_id) REFERENCES members(member_id)
);

CREATE TABLE IF NOT EXISTS utilization (
    utilization_id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    service_type TEXT NOT NULL,
    units_used INTEGER NOT NULL,
    limit_units INTEGER NOT NULL,
    FOREIGN KEY(member_id) REFERENCES members(member_id)
);

CREATE TABLE IF NOT EXISTS benefits (
    benefit_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    service_category TEXT NOT NULL,
    copay REAL NOT NULL,
    coinsurance REAL NOT NULL,
    preauth_required INTEGER NOT NULL
);
"""


def init_payer_db(db_path: str) -> sqlite3.Connection:
    """Initialize the 6 required Payer DB tables in SQLite with full schema compatibility."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(CREATE_PAYER_TABLES)
    conn.commit()
    return conn


def get_payer_db_tables(db_path: str) -> list:
    """Return list of table names in Payer DB."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables
