import sqlite3
from database.db_manager import get_db_connection

class PatientRepository:
    def __init__(self):
        pass

    def get_patient(self, patient_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE patient_id = ?;", (patient_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_conditions(self, patient_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conditions WHERE patient_id = ? ORDER BY onset DESC;", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_medications(self, patient_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medications WHERE patient_id = ? ORDER BY date DESC;", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_observations(self, patient_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM observations WHERE patient_id = ? ORDER BY date DESC;", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_procedures(self, patient_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM procedures WHERE patient_id = ? ORDER BY date DESC;", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_encounters(self, patient_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM encounters WHERE patient_id = ? ORDER BY date DESC;", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_documents(self, patient_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE patient_id = ? ORDER BY date DESC;", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_patients(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients ORDER BY last_name, first_name;")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
