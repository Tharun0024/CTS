"""
Evidence Module: Support available vs. submitted evidence, provenance, and clinical criteria metrics
"""
from dataclasses import dataclass
from typing import Optional
import datetime


@dataclass
class EvidenceRecord:
    evidence_id: str
    patient_id: str
    source_record_id: str
    document_id: str
    evidence_type: str
    event_date: str
    content_reference: str
    provenance: str
    is_submitted: bool = True
    kl_grade: Optional[int] = None
    pt_weeks_completed: Optional[int] = None
    neurological_deficit: Optional[bool] = None
    abnormal_stress_test: Optional[bool] = None
    refractory_angina: Optional[bool] = None


def create_evidence(
    evidence_id: str,
    patient_id: str,
    evidence_type: str,
    event_date: str,
    content_reference: str,
    source_record_id: Optional[str] = None,
    document_id: Optional[str] = None,
    provenance: str = "EMR_ST_JUDE_CLINIC",
    is_submitted: bool = True,
    auth_request_date: Optional[str] = None,
    kl_grade: Optional[int] = None,
    pt_weeks_completed: Optional[int] = None,
    neurological_deficit: Optional[bool] = None,
    abnormal_stress_test: Optional[bool] = None,
    refractory_angina: Optional[bool] = None
) -> EvidenceRecord:
    """
    Construct evidence record with structured clinical criteria attributes and provenance.
    """
    source_id = source_record_id or f"SRC_{evidence_id}"
    doc_id = document_id or f"DOC_{evidence_id}"
    
    if auth_request_date:
        event_dt = datetime.datetime.fromisoformat(event_date.replace("Z", ""))
        auth_dt = datetime.datetime.fromisoformat(auth_request_date.replace("Z", ""))
        if event_dt > auth_dt:
            pass

    return EvidenceRecord(
        evidence_id=evidence_id,
        patient_id=patient_id,
        source_record_id=source_id,
        document_id=doc_id,
        evidence_type=evidence_type,
        event_date=event_date,
        content_reference=content_reference,
        provenance=provenance,
        is_submitted=is_submitted,
        kl_grade=kl_grade,
        pt_weeks_completed=pt_weeks_completed,
        neurological_deficit=neurological_deficit,
        abnormal_stress_test=abnormal_stress_test,
        refractory_angina=refractory_angina
    )
