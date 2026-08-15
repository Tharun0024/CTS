import os
import json
import sqlite3
from datetime import datetime
from config import FHIR_DIR, DB_PATH
from database.db_manager import get_db_connection, init_db

def import_fhir_bundles(limit=None):
    """Parses Synthea FHIR JSON bundles and loads them into SQLite."""
    print("Initializing database...")
    init_db()

    if not os.path.exists(FHIR_DIR):
        print(f"Error: FHIR directory not found at: {FHIR_DIR}")
        return

    all_files = [f for f in os.listdir(FHIR_DIR) if f.endswith('.json')]
    if limit:
        all_files = all_files[:limit]
        print(f"Limiting import to first {limit} files.")

    print(f"Found {len(all_files)} FHIR bundle files to process.")

    patients_list = []
    conditions_list = []
    medications_list = []
    observations_list = []
    procedures_list = []
    encounters_list = []
    
    conn = get_db_connection()
    cursor = conn.cursor()

    for idx, fname in enumerate(all_files):
        fpath = os.path.join(FHIR_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                bundle = json.load(f)
                
            patient_id = None
            
            # First pass: find Patient resource to get patient ID
            for entry in bundle.get('entry', []):
                resource = entry.get('resource', {})
                if resource.get('resourceType') == 'Patient':
                    patient_id = resource.get('id', '')
                    
                    # Extract demographics
                    names = resource.get('name', [])
                    name = "Unknown"
                    if names:
                        given = " ".join(names[0].get("given", []))
                        family = names[0].get("family", "")
                        name = f"{given} {family}".strip()
                    dob = resource.get("birthDate", "Unknown")
                    gender = resource.get("gender", "Unknown")
                    
                    # Address
                    addresses = resource.get("address", [])
                    addr_str = "Unknown"
                    if addresses:
                        addr = addresses[0]
                        line = ", ".join(addr.get("line", []))
                        city = addr.get("city", "")
                        state = addr.get("state", "")
                        zip_code = addr.get("postalCode", "")
                        addr_str = f"{line}, {city}, {state} {zip_code}".strip()
                        
                    patients_list.append((patient_id, name, dob, gender, addr_str))
                    break

            if not patient_id:
                # No patient record in this bundle
                continue

            # Second pass: process clinical resources
            for entry in bundle.get('entry', []):
                resource = entry.get('resource', {})
                res_type = resource.get('resourceType')
                res_id = resource.get('id', '')
                
                if res_type == 'Condition':
                    code_coding = resource.get("code", {}).get("coding", [{}])
                    code = code_coding[0].get("code", "")
                    system = code_coding[0].get("system", "")
                    display = code_coding[0].get("display", resource.get("code", {}).get("text", "Unknown Condition"))
                    onset = resource.get("onsetDateTime") or resource.get("recordedDate") or "Unknown"
                    status = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active")
                    
                    conditions_list.append((res_id, patient_id, code, system, display, onset, status))
                    
                elif res_type == 'MedicationRequest':
                    med_coding = resource.get("medicationCodeableConcept", {}).get("coding", [{}])
                    code = med_coding[0].get("code", "")
                    system = med_coding[0].get("system", "")
                    display = med_coding[0].get("display", resource.get("medicationCodeableConcept", {}).get("text", "Unknown Medication"))
                    date = resource.get("authoredOn") or "Unknown"
                    status = resource.get("status", "active")
                    doctor = resource.get("requester", {}).get("display", "Unknown Clinician")
                    
                    medications_list.append((res_id, patient_id, code, system, display, date, status, doctor))
                    
                elif res_type == 'Observation':
                    if "valueQuantity" in resource:
                        code_coding = resource.get("code", {}).get("coding", [{}])
                        code = code_coding[0].get("code", "")
                        system = code_coding[0].get("system", "")
                        display = code_coding[0].get("display", resource.get("code", {}).get("text", "Unknown Observation"))
                        val_qty = resource.get("valueQuantity", {})
                        value = val_qty.get("value")
                        unit = val_qty.get("unit", "")
                        date = resource.get("effectiveDateTime") or resource.get("issued") or "Unknown"
                        
                        observations_list.append((res_id, patient_id, code, system, display, value, unit, date))
                        
                elif res_type == 'Procedure':
                    code_coding = resource.get("code", {}).get("coding", [{}])
                    code = code_coding[0].get("code", "")
                    system = code_coding[0].get("system", "")
                    display = code_coding[0].get("display", resource.get("code", {}).get("text", "Unknown Procedure"))
                    date = resource.get("performedDateTime") or (resource.get("performedPeriod", {}).get("start")) or "Unknown"
                    status = resource.get("status", "completed")
                    performer = "Unknown Clinician"
                    performers = resource.get("performer", [])
                    if performers:
                        performer = performers[0].get("actor", {}).get("display", "Unknown Clinician")
                        
                    procedures_list.append((res_id, patient_id, code, system, display, date, status, performer))
                    
                elif res_type == 'Encounter':
                    code_coding = resource.get("type", [{}])[0].get("coding", [{}])
                    code = code_coding[0].get("code", "")
                    system = code_coding[0].get("system", "")
                    display = code_coding[0].get("display", resource.get("type", [{}])[0].get("text", "Unknown Encounter"))
                    date = resource.get("period", {}).get("start") or "Unknown"
                    status = resource.get("status", "finished")
                    
                    encounters_list.append((res_id, patient_id, code, system, display, date, status))

        except Exception as e:
            print(f"Error parsing file {fname}: {e}")

    # Bulk insert into database
    print(f"Writing data to database ({DB_PATH})...")
    
    try:
        cursor.executemany("INSERT OR REPLACE INTO patients VALUES (?, ?, ?, ?, ?);", patients_list)
        cursor.executemany("INSERT OR REPLACE INTO conditions VALUES (?, ?, ?, ?, ?, ?, ?);", conditions_list)
        cursor.executemany("INSERT OR REPLACE INTO medications VALUES (?, ?, ?, ?, ?, ?, ?, ?);", medications_list)
        cursor.executemany("INSERT OR REPLACE INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?);", observations_list)
        cursor.executemany("INSERT OR REPLACE INTO procedures VALUES (?, ?, ?, ?, ?, ?, ?, ?);", procedures_list)
        cursor.executemany("INSERT OR REPLACE INTO encounters VALUES (?, ?, ?, ?, ?, ?, ?);", encounters_list)
        
        conn.commit()
        print("Data import complete!")
        print(f"  Patients:     {len(patients_list)}")
        print(f"  Conditions:   {len(conditions_list)}")
        print(f"  Medications:  {len(medications_list)}")
        print(f"  Observations: {len(observations_list)}")
        print(f"  Procedures:   {len(procedures_list)}")
        print(f"  Encounters:   {len(encounters_list)}")
    except Exception as e:
        conn.rollback()
        print(f"Database write failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Import first 15 files for quick development/testing
    import_fhir_bundles(limit=15)
