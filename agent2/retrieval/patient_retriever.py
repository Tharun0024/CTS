from datetime import datetime
from typing import List
from schemas.evidence import Evidence
from database.repositories.patient_repository import PatientRepository

class PatientEvidenceRetriever:
    def __init__(self):
        self.patient_repo = PatientRepository()

    def retrieve_all_evidence(self, patient_id: str) -> List[Evidence]:
        """Queries all clinical tables and returns a unified list of Evidence objects."""
        evidence_list = []
        retrieved_at = datetime.utcnow().isoformat() + "Z"

        # 1. Retrieve Conditions
        conditions = self.patient_repo.get_conditions(patient_id)
        for cond in conditions:
            evidence_list.append(Evidence(
                evidence_id=f"EV-COND-{cond['id']}",
                patient_id=patient_id,
                source_type="conditions",
                source_record_id=cond['id'],
                event_date=cond['onset'],
                content=f"Diagnosis: {cond['display']} (Code: {cond['code']}, System: {cond['system']}) [Status: {cond['status']}]",
                relevance_score=1.0,
                evidence_type="CLINICAL",
                retrieved_at=retrieved_at
            ))

        # 2. Retrieve Medications
        medications = self.patient_repo.get_medications(patient_id)
        for med in medications:
            evidence_list.append(Evidence(
                evidence_id=f"EV-MED-{med['id']}",
                patient_id=patient_id,
                source_type="medications",
                source_record_id=med['id'],
                event_date=med['date'],
                content=f"Medication: {med['display']} (Code: {med['code']}) [Status: {med['status']}], prescribed by {med['doctor']}",
                relevance_score=1.0,
                evidence_type="MEDICATION",
                retrieved_at=retrieved_at
            ))

        # 3. Retrieve Observations (Labs)
        observations = self.patient_repo.get_observations(patient_id)
        for obs in observations:
            evidence_list.append(Evidence(
                evidence_id=f"EV-OBS-{obs['id']}",
                patient_id=patient_id,
                source_type="observations",
                source_record_id=obs['id'],
                event_date=obs['date'],
                content=f"Observation/Lab: {obs['display']} (Code: {obs['code']}) = {obs['value']} {obs['unit']}",
                relevance_score=1.0,
                evidence_type="LAB" if "cholesterol" in obs['display'].lower() or "hemoglobin" in obs['display'].lower() or "hba1c" in obs['display'].lower() else "OBSERVATION",
                retrieved_at=retrieved_at
            ))

        # 4. Retrieve Procedures
        procedures = self.patient_repo.get_procedures(patient_id)
        for proc in procedures:
            evidence_list.append(Evidence(
                evidence_id=f"EV-PROC-{proc['id']}",
                patient_id=patient_id,
                source_type="procedures",
                source_record_id=proc['id'],
                event_date=proc['date'],
                content=f"Procedure: {proc['display']} (Code: {proc['code']}) [Status: {proc['status']}], performed by {proc['doctor']}",
                relevance_score=1.0,
                evidence_type="PROCEDURE",
                retrieved_at=retrieved_at
            ))

        # 5. Retrieve Encounters
        encounters = self.patient_repo.get_encounters(patient_id)
        for enc in encounters:
            evidence_list.append(Evidence(
                evidence_id=f"EV-ENC-{enc['id']}",
                patient_id=patient_id,
                source_type="encounters",
                source_record_id=enc['id'],
                event_date=enc['date'],
                content=f"Encounter: {enc['display']} (Code: {enc['code']}) [Status: {enc['status']}]",
                relevance_score=1.0,
                evidence_type="CLINICAL",
                retrieved_at=retrieved_at
            ))

        # 6. Retrieve Documents (Clinical notes)
        documents = self.patient_repo.get_documents(patient_id)
        for doc in documents:
            evidence_list.append(Evidence(
                evidence_id=f"EV-DOC-{doc['id']}",
                patient_id=patient_id,
                source_type="documents",
                source_record_id=doc['id'],
                event_date=doc['date'],
                content=f"Document ({doc['type']}): {doc['title']} - Content: {doc['content']}",
                relevance_score=1.0,
                evidence_type="DOCUMENT",
                retrieved_at=retrieved_at
            ))

        return evidence_list
