import sqlite3
import os
import sys

# Try to import from config with fallback
try:
    from agent2.config import DB_PATH
except ImportError:
    # Fallback: use default path
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_PATH = os.path.join(PROJECT_ROOT, "agent2", "workspace", "agent2.db")

def get_db_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite database with clinical and metadata tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # ==========================================
    # 1. PROVIDER CLINICAL DATA (Big Patient Record)
    # ==========================================
    
    # Patients Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        dob TEXT,
        gender TEXT,
        address TEXT
    );
    """)

    # Conditions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conditions (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        code TEXT,
        system TEXT,
        display TEXT,
        onset TEXT,
        status TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
    );
    """)

    # Medications Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medications (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        code TEXT,
        system TEXT,
        display TEXT,
        date TEXT,
        status TEXT,
        doctor TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
    );
    """)

    # Observations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        code TEXT,
        system TEXT,
        display TEXT,
        value REAL,
        unit TEXT,
        date TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
    );
    """)

    # Procedures Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS procedures (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        code TEXT,
        system TEXT,
        display TEXT,
        date TEXT,
        status TEXT,
        doctor TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
    );
    """)

    # Encounters Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS encounters (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        code TEXT,
        system TEXT,
        display TEXT,
        date TEXT,
        status TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
    );
    """)

    # Documents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        title TEXT,
        content TEXT,
        type TEXT,
        date TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
    );
    """)

    # ==========================================
    # 2. AGENT 2 WORKFLOW & TRACKING DATA
    # ==========================================
    
    # Claims Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS claims (
        claim_id TEXT PRIMARY KEY,
        patient_id TEXT,
        provider_id TEXT,
        payer_id TEXT,
        payer_type TEXT,
        policy_id TEXT,
        current_version INTEGER DEFAULT 1,
        status TEXT,
        created_at TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
    );
    """)

    # Claim Versions Table (Immutable historical snapshots)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS claim_versions (
        claim_id TEXT,
        version INTEGER,
        canonical_claim_json TEXT,
        status TEXT,
        created_at TEXT,
        previous_version INTEGER,
        PRIMARY KEY (claim_id, version),
        FOREIGN KEY(claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE
    );
    """)

    # Submissions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        submission_id TEXT PRIMARY KEY,
        claim_id TEXT,
        claim_version INTEGER,
        submitted_at TEXT,
        status TEXT,
        attempt_number INTEGER,
        idempotency_key TEXT,
        payer_response_json TEXT,
        FOREIGN KEY(claim_id, claim_version) REFERENCES claim_versions(claim_id, version)
    );
    """)

    # Criterion Results Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS criterion_results (
        claim_id TEXT,
        claim_version INTEGER,
        criterion_id TEXT,
        status TEXT,
        evidence_ids TEXT,
        policy_reference TEXT,
        reason TEXT,
        PRIMARY KEY(claim_id, claim_version, criterion_id),
        FOREIGN KEY(claim_id, claim_version) REFERENCES claim_versions(claim_id, version) ON DELETE CASCADE
    );
    """)

    # Evidence Matches Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence_matches (
        claim_id TEXT,
        claim_version INTEGER,
        criterion_id TEXT,
        evidence_id TEXT,
        match_type TEXT,
        confidence REAL,
        created_at TEXT,
        PRIMARY KEY(claim_id, claim_version, criterion_id, evidence_id),
        FOREIGN KEY(claim_id, claim_version) REFERENCES claim_versions(claim_id, version) ON DELETE CASCADE
    );
    """)

    # Human Reviews Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS human_reviews (
        review_id TEXT PRIMARY KEY,
        claim_id TEXT,
        reason TEXT,
        failed_criteria TEXT,
        missing_information TEXT,
        uncertain_information TEXT,
        recommended_action TEXT,
        created_at TEXT,
        FOREIGN KEY(claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE
    );
    """)

    # Audit Log Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent2_audit (
        audit_id TEXT PRIMARY KEY,
        correlation_id TEXT,
        claim_id TEXT,
        claim_version INTEGER,
        state_before TEXT,
        state_after TEXT,
        action TEXT,
        timestamp TEXT,
        result TEXT,
        error TEXT
    );
    """)

    # Provider Decisions Table (Phase 4: persisted accept/decline consent on
    # recovered evidence; append-only history, never updated in place)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS provider_decisions (
        decision_id TEXT PRIMARY KEY,
        claim_id TEXT,
        claim_version INTEGER,
        decision TEXT,
        evidence_ids TEXT,
        evidence_request_id TEXT,
        correlation_id TEXT,
        reason TEXT,
        decided_at TEXT,
        FOREIGN KEY(claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE
    );
    """)

    # Claim Records Table (Phase 5A: API boundary snapshots of the current
    # claim state; the immutable version history lives inside record_json)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS claim_records (
        claim_id TEXT PRIMARY KEY,
        patient_id TEXT,
        status TEXT,
        record_json TEXT,
        updated_at TEXT
    );
    """)

    # Simulation Records Table (Phase 5B: simulation run snapshots carrying
    # the simulation -> patient -> claim relationships inside record_json)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulation_records (
        simulation_id TEXT PRIMARY KEY,
        status TEXT,
        record_json TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    """)

    conn.commit()
    conn.close()
    print("Database schema initialized successfully at:", DB_PATH)

if __name__ == "__main__":
    init_db()
