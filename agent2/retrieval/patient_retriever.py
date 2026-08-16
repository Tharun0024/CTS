from datetime import datetime
from typing import List, Dict, Optional
from ..schemas.evidence import Evidence, EvidenceState
from ..database.repositories.patient_repository import PatientRepository

class PatientEvidenceRetriever:
    def __init__(self):
        self.patient_repo = PatientRepository()

    def retrieve_all_evidence(self, patient_id: str) -> List[Evidence]:
        """Queries all clinical tables and returns a unified list of Evidence objects with state=FOUND."""
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
                state=EvidenceState.FOUND,
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
                state=EvidenceState.FOUND,
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
                state=EvidenceState.FOUND,
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
                state=EvidenceState.FOUND,
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
                state=EvidenceState.FOUND,
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
                state=EvidenceState.FOUND,
                relevance_score=1.0,
                evidence_type="DOCUMENT",
                retrieved_at=retrieved_at
            ))

        return evidence_list

    def retrieve_targeted_evidence(self, patient_id: str, clinical_concepts: List[str]) -> Dict[str, List[Evidence]]:
        """
        Search for evidence matching specific clinical concepts.
        Returns dict with 'found' and 'missing' evidence lists.
        """
        all_evidence = self.retrieve_all_evidence(patient_id)
        found_evidence = []
        missing_concepts = []
        
        concept_mapping = {
            "ldl": self._search_ldl_evidence,
            "statin": self._search_statin_evidence,
            "hemoglobin": self._search_hemoglobin_evidence,
            "iron": self._search_iron_evidence,
            "metformin": self._search_metformin_evidence,
            "hba1c": self._search_hba1c_evidence,
            "physical therapy": self._search_pt_evidence,
            "imaging": self._search_imaging_evidence,
            "age": self._search_age_evidence,
            "diagnosis": self._search_diagnosis_evidence,
        }
        
        for concept in clinical_concepts:
            concept_lower = concept.lower()
            matched = False
            
            # Try exact concept mapping
            if concept_lower in concept_mapping:
                matches = concept_mapping[concept_lower](all_evidence)
                if matches:
                    found_evidence.extend(matches)
                    matched = True
            
            # If no exact match, search for concept in evidence content
            if not matched:
                for evidence in all_evidence:
                    if concept_lower in evidence.content.lower():
                        found_evidence.append(evidence)
                        matched = True
            
            if not matched:
                missing_concepts.append(concept)
        
        # Create missing evidence entries for concepts not found
        missing_evidence = []
        retrieved_at = datetime.utcnow().isoformat() + "Z"
        for concept in missing_concepts:
            missing_evidence.append(Evidence(
                evidence_id=f"EV-MISSING-{concept.upper().replace(' ', '_')}",
                patient_id=patient_id,
                source_type="missing",
                source_record_id="",
                event_date="",
                content=f"Missing evidence for: {concept}",
                state=EvidenceState.MISSING,
                relevance_score=0.0,
                evidence_type="MISSING",
                retrieved_at=retrieved_at
            ))
        
        return {
            "found": list(set(found_evidence)),  # Deduplicate
            "missing": missing_evidence
        }
    
    # Concept-specific search methods
    def _search_ldl_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        return [e for e in evidence_list if "ldl" in e.content.lower() or "18262-6" in e.content]
    
    def _search_statin_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        statin_terms = ["simvastatin", "atorvastatin", "rosuvastatin", "statin"]
        return [e for e in evidence_list if any(term in e.content.lower() for term in statin_terms)]
    
    def _search_hemoglobin_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        return [e for e in evidence_list if "hemoglobin" in e.content.lower() or "718-7" in e.content]
    
    def _search_iron_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        return [e for e in evidence_list if "iron" in e.content.lower() or "ferrous" in e.content.lower()]
    
    def _search_metformin_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        return [e for e in evidence_list if "metformin" in e.content.lower()]
    
    def _search_hba1c_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        return [e for e in evidence_list if "hba1c" in e.content.lower() or "4548-4" in e.content]
    
    def _search_pt_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        pt_terms = ["physical therapy", "pt", "rehabilitation"]
        return [e for e in evidence_list if any(term in e.content.lower() for term in pt_terms)]
    
    def _search_imaging_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        imaging_terms = ["x-ray", "xray", "radiograph", "mri", "ct", "imaging", "ultrasound"]
        return [e for e in evidence_list if any(term in e.content.lower() for term in imaging_terms)]
    
    def _search_age_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        # Age is usually in conditions or encounters
        return [e for e in evidence_list if "age" in e.content.lower() or "birth" in e.content.lower()]
    
    def _search_diagnosis_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        return [e for e in evidence_list if e.source_type == "conditions"]
