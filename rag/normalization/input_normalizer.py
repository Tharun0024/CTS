import re
from typing import Dict, Any
from models.rag_models import ClaimInput

def normalize_payer_name(payer: str) -> str:
    """
    Standardize payer names.
    e.g., 'CMS', 'Medicare', 'CMS Medicare' -> 'CMS (Medicare)'
    'Aetna', 'AETNA' -> 'Aetna'
    """
    payer_clean = payer.strip().lower()
    if "cms" in payer_clean or "medicare" in payer_clean:
        return "CMS (Medicare)"
    if "aetna" in payer_clean:
        return "Aetna"
    return payer.strip()

def normalize_policy_id(policy_id: str) -> str:
    """
    Normalize Policy ID formatting.
    """
    if not policy_id:
        return ""
    # Strip spaces, uppercase
    val = policy_id.strip().upper()
    # Normalize prefixes: e.g., 'CPB0660' -> 'CPB-0660'
    # 'NCD20.8.3' -> 'NCD-20.8.3'
    # Let's match prefixes like CPB, NCD, LCD
    match = re.match(r"^(CPB|NCD|LCD)[\s-]?([\d\.\-]+)$", val)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return val

def normalize_code(code: str) -> str:
    """
    Remove dots, spaces, hyphens for internal matching, but retain standardized clean display format.
    """
    if not code:
        return ""
    return code.strip().upper()

def normalize_claim_input(claim: ClaimInput) -> ClaimInput:
    """
    Produce a normalized version of the incoming claim.
    """
    # Normalize payer and policy ID
    payer = normalize_payer_name(claim.insurance.primary.payer)
    policy_id = None
    if claim.insurance.primary.policy_id:
        policy_id = normalize_policy_id(claim.insurance.primary.policy_id)
    
    # Normalize diagnoses
    norm_diag = []
    for diag in claim.diagnosis:
        norm_diag.append({
            "code": normalize_code(diag.code),
            "description": diag.description.strip()
        })
        
    # Normalize procedure
    norm_proc = {
        "code": normalize_code(claim.procedure.code),
        "description": claim.procedure.description.strip()
    }
    
    # Return a new ClaimInput with normalized details
    return ClaimInput(
        claim_id=claim.claim_id.strip(),
        insurance={
            "primary": {
                "payer": payer,
                "policy_id": policy_id
            }
        },
        diagnosis=norm_diag,
        procedure=norm_proc,
        clinical_domain=claim.clinical_domain.strip().lower()
    )
