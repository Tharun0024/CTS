import os
import json
from typing import List
from abc import ABC, abstractmethod
from config import POLICIES_DIR, CMS_JSONL_PATH
from schemas.policy import PolicyCriterion
from schemas.evidence import PolicyEvidence

class PolicyRetriever(ABC):
    @abstractmethod
    def retrieve_criteria(self, policy_id: str) -> List[PolicyCriterion]:
        pass

    @abstractmethod
    def retrieve_policy_evidence(self, policy_id: str) -> List[PolicyEvidence]:
        pass


class CommercialPolicyRetriever(PolicyRetriever):
    """Retrieves and normalizes commercial insurance policies from local markdown files."""
    
    def retrieve_criteria(self, policy_id: str) -> List[PolicyCriterion]:
        policy_id_lower = policy_id.lower()
        criteria = []

        if "epogen" in policy_id_lower:
            criteria = [
                PolicyCriterion(
                    criterion_id="C01",
                    description="Age: Patient must be 18 years of age or older.",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 1"
                ),
                PolicyCriterion(
                    criterion_id="C02",
                    description="Diagnosis: Patient must have a documented diagnosis of Anemia (SNOMED code 271737000 or description containing Anemia).",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 2"
                ),
                PolicyCriterion(
                    criterion_id="C03",
                    description="Clinical Lab: Most recent Hemoglobin (Hb) level must be less than 10.0 g/dL (LOINC 718-7) within the past 60 days.",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 3"
                ),
                PolicyCriterion(
                    criterion_id="C04",
                    description="Step Therapy: Patient must have had a trial of oral iron supplementation therapy (or an active prescription of iron or multivitamin containing iron).",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 4"
                ),
                PolicyCriterion(
                    criterion_id="C05",
                    description="Contraindications: Patient must not have uncontrolled hypertension. If history of Essential Hypertension, most recent Systolic BP must be below 160 mmHg.",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 5"
                ),
            ]
        elif "humulin" in policy_id_lower:
            criteria = [
                PolicyCriterion(
                    criterion_id="C01",
                    description="Diagnosis: Patient must have a documented diagnosis of Diabetes mellitus type 2 (SNOMED 44054006).",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 1"
                ),
                PolicyCriterion(
                    criterion_id="C02",
                    description="First-Line Step-Therapy: Failure of glycemic control despite an active trial of Metformin (Metformin hydrochloride or similar) for at least 90 days.",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 2"
                ),
                PolicyCriterion(
                    criterion_id="C03",
                    description="HbA1c Lab Monitoring: Glycated Hemoglobin (HbA1c) level (LOINC 4548-4) must be documented in history within the past 180 days to establish baseline.",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 3"
                ),
            ]
        elif "repatha" in policy_id_lower:
            criteria = [
                PolicyCriterion(
                    criterion_id="C01",
                    description="Age: Patient must be 18 years of age or older.",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 1"
                ),
                PolicyCriterion(
                    criterion_id="C02",
                    description="Diagnosis: Documented diagnosis of Hyperlipidemia (SNOMED code 166110001 or description Hyperlipidemia).",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 2"
                ),
                PolicyCriterion(
                    criterion_id="C03",
                    description="Statin Step-Therapy: Inadequate response (failure to achieve LDL-C targets) after at least 90 days of active therapy with Simvastatin, Atorvastatin, or Rosuvastatin.",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 3"
                ),
                PolicyCriterion(
                    criterion_id="C04",
                    description="Clinical Lab: Most recent LDL-Cholesterol level must be greater than or equal to 100 mg/dL (LOINC 18262-6) within the past 90 days.",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 4"
                ),
                PolicyCriterion(
                    criterion_id="C05",
                    description="Specialist Consult: Prescribed by, or in consultation with, a Cardiologist or Endocrinologist.",
                    required=True,
                    source="AETNA",
                    policy_reference=f"{policy_id} Sec 5"
                ),
            ]
        return criteria

    def retrieve_policy_evidence(self, policy_id: str) -> List[PolicyEvidence]:
        policy_id_lower = policy_id.lower()
        filename = ""
        for name in os.listdir(POLICIES_DIR):
            if policy_id_lower in name.lower():
                filename = name
                break

        if not filename:
            return []

        filepath = os.path.join(POLICIES_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split policy into logical evidence chunks mapped to criteria
        evidence_chunks = []
        lines = content.split('\n')
        current_sec = "Overview"
        current_text = []

        for line in lines:
            if line.startswith("## ") or line.startswith("### "):
                if current_text:
                    evidence_chunks.append(PolicyEvidence(
                        policy_id=policy_id,
                        policy_source="AETNA",
                        section=current_sec,
                        criterion_id="ALL",
                        text="\n".join(current_text).strip()
                    ))
                current_sec = line.replace('#', '').strip()
                current_text = []
            else:
                current_text.append(line)

        if current_text:
            evidence_chunks.append(PolicyEvidence(
                policy_id=policy_id,
                policy_source="AETNA",
                section=current_sec,
                criterion_id="ALL",
                text="\n".join(current_text).strip()
            ))

        return evidence_chunks


class CMSPolicyRetriever(PolicyRetriever):
    """Retrieves and normalizes Medicare/CMS policies from the local JSONL reference database."""

    def __init__(self):
        self.chunks = []
        self.load_cms_policies()

    def load_cms_policies(self):
        if not os.path.exists(CMS_JSONL_PATH):
            return
        with open(CMS_JSONL_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    self.chunks.append(json.loads(line))

    def retrieve_criteria(self, policy_id: str) -> List[PolicyCriterion]:
        criteria = []
        # Filter chunks matching the policy ID
        policy_chunks = [c for c in self.chunks if c["policy_id"].lower() == policy_id.lower()]
        
        if not policy_chunks:
            # Fallback for Total Knee Arthroplasty (LCD-L36575) if matched by name
            if "knee" in policy_id.lower() or "l36575" in policy_id.lower():
                policy_chunks = [c for c in self.chunks if "l36575" in c["policy_id"].lower() or "l36039" in c["policy_id"].lower()]

        for chunk in policy_chunks:
            cid = chunk.get("criterion_id", "C01")
            
            # Map specific CMS policies to normalized criteria lists
            if "L36575" in chunk["policy_id"] or "L36039" in chunk["policy_id"]:
                criteria = [
                    PolicyCriterion(
                        criterion_id="C01",
                        description="Medical Necessity: Advanced joint disease shown on imaging (radiography, MRI, or CT) + pain or functional disability.",
                        required=True,
                        source="CMS (Medicare)",
                        policy_reference=f"{chunk['policy_id']} - {chunk['section']}"
                    ),
                    PolicyCriterion(
                        criterion_id="C02",
                        description="Conservative Therapy: History of unsuccessful conservative (non-surgical) therapy (e.g., physical therapy for at least 6 weeks / 42 days).",
                        required=True,
                        source="CMS (Medicare)",
                        policy_reference=f"{chunk['policy_id']} - {chunk['section']}"
                    ),
                    PolicyCriterion(
                        criterion_id="C03",
                        description="No Contraindications: No active joint or systemic infection, open wound at surgical site, or rapidly progressive neurological disease.",
                        required=True,
                        source="CMS (Medicare)",
                        policy_reference=f"{chunk['policy_id']} - {chunk['section']}"
                    )
                ]
            else:
                # Generic fallback if not Knee Arthroplasty
                criteria.append(PolicyCriterion(
                    criterion_id=cid,
                    description=chunk.get("criterion_name", chunk.get("policy_title", "")) + ": " + chunk.get("text", ""),
                    required=True,
                    source="CMS (Medicare)",
                    policy_reference=f"{chunk['policy_id']} - {chunk['section']}"
                ))

        return criteria

    def retrieve_policy_evidence(self, policy_id: str) -> List[PolicyEvidence]:
        evidence_list = []
        policy_chunks = [c for c in self.chunks if c["policy_id"].lower() == policy_id.lower()]
        
        if not policy_chunks and ("knee" in policy_id.lower() or "l36575" in policy_id.lower()):
            policy_chunks = [c for c in self.chunks if "l36575" in c["policy_id"].lower() or "l36039" in c["policy_id"].lower()]

        for chunk in policy_chunks:
            evidence_list.append(PolicyEvidence(
                policy_id=chunk["policy_id"],
                policy_source="CMS (Medicare)",
                section=chunk["section"],
                criterion_id=chunk.get("criterion_id", "C01"),
                text=chunk["text"]
            ))
        return evidence_list


class PolicyRouter:
    """Dispatches policy retrieval to the correct engine based on Payer Type."""
    
    @staticmethod
    def retrieve(payer_type: str, policy_id: str) -> tuple:
        if payer_type.upper() == "MEDICARE" or "CMS" in policy_id.upper() or "NCD" in policy_id.upper() or "LCD" in policy_id.upper():
            retriever = CMSPolicyRetriever()
        else:
            retriever = CommercialPolicyRetriever()
            
        criteria = retriever.retrieve_criteria(policy_id)
        evidence = retriever.retrieve_policy_evidence(policy_id)
        return criteria, evidence
