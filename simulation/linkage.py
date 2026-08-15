"""
Linkage Module: Handles Patient -> Member -> Payer -> Plan -> Policy References via RAG Loader
"""
import os
import json
from dataclasses import dataclass
from typing import Dict, Optional, Any


class RAGRetrievalError(Exception):
    """Raised when RAG policy retrieval fails (e.g. index corruption, network error)."""
    pass


def load_rag_policy_dataset() -> Dict[str, Dict[str, Any]]:
    """Loads external RAG policy dataset JSON as single source of truth."""
    dataset_path = os.path.join(os.path.dirname(__file__), "policy_rag_dataset.json")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"RAG policy dataset not found at {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def retrieve_policy_from_rag(policy_id: str, lookup_mode: str = "normal") -> Optional[Dict[str, Any]]:
    """
    RAG Policy Retrieval Engine:
    Retrieves policy definition from external RAG dataset.
    Simulates genuine retrieval failure when lookup_mode == 'intentional_rag_failure'.
    """
    if lookup_mode == "intentional_rag_failure":
        raise RAGRetrievalError(f"RAG policy retrieval pipeline failed for policy_id '{policy_id}': Index corrupted or unavailable.")
    
    rag_dataset = load_rag_policy_dataset()
    return rag_dataset.get(policy_id)


@dataclass
class PayerLinkage:
    patient_id: str
    member_id: str
    payer_id: str
    plan_id: str
    policy_id: Optional[str]
    is_mismatch_scenario: bool = False
    policy_lookup_mode: str = "normal"  # "normal", "intentional_rag_failure", "no_policy_established"
    failure_reason: Optional[str] = None


def create_patient_payer_linkage(
    patient_id: str,
    payer_id: str = "Aetna",
    plan_id: str = "AETNA_GOLD_PPO",
    policy_id: Optional[str] = "AETNA_POL_KNEE_01",
    mismatch: bool = False,
    policy_lookup_mode: str = "normal",
    failure_reason: Optional[str] = None
) -> PayerLinkage:
    """
    Create valid patient to member to payer linkage.
    Matching patient_id and member_id unless explicit mismatch scenario.
    """
    member_id = patient_id if not mismatch else f"MEM_MISMATCH_{patient_id}"
    
    if policy_id and policy_lookup_mode == "normal":
        dataset = load_rag_policy_dataset()
        if policy_id not in dataset:
            print(f"MISSING POLICY IN RAG: {policy_id}")
    
    return PayerLinkage(
        patient_id=patient_id,
        member_id=member_id,
        payer_id=payer_id,
        plan_id=plan_id,
        policy_id=policy_id if policy_lookup_mode != "no_policy_established" else None,
        is_mismatch_scenario=mismatch,
        policy_lookup_mode=policy_lookup_mode,
        failure_reason=failure_reason
    )
