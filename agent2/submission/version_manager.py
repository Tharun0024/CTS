import json
from datetime import datetime
from database.repositories.claim_repository import ClaimRepository
from schemas.claim import CanonicalClaim

class VersionManager:
    """Manages the creation and tracking of immutable claim versions."""
    
    def __init__(self):
        self.claim_repo = ClaimRepository()

    def create_new_version(self, claim: CanonicalClaim, status: str) -> CanonicalClaim:
        """Increments the claim version, registers the new immutable version in DB, and returns the updated claim."""
        previous_version = claim.claim_version
        new_version = previous_version + 1
        
        # 1. Update version field on claim
        claim_dict = claim.model_dump()
        claim_dict["claim_version"] = new_version
        new_claim = CanonicalClaim(**claim_dict)
        
        # 2. Persist in database
        self.claim_repo.create_claim_version(
            claim_id=new_claim.claim_id,
            version=new_claim.claim_version,
            canonical_claim_json=new_claim.model_dump_json(),
            status=status,
            previous_version=previous_version
        )
        
        return new_claim
