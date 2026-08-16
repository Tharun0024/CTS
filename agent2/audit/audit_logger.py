import uuid
from ..database.repositories.audit_repository import AuditRepository

class AuditLogger:
    """Orchestrates structured audit logging for state transitions and claims activities."""
    
    def __init__(self, correlation_id: str = None):
        self.audit_repo = AuditRepository()
        self.correlation_id = correlation_id if correlation_id else f"A2RUN-{uuid.uuid4().hex[:6].upper()}"

    def log_transition(self, claim_id: str, version: int, state_before: str, state_after: str, action: str, result: str = None, error: str = None):
        """Logs a lifecycle state transition or clinical action in SQLite and prints it."""
        audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        
        self.audit_repo.log_audit(
            audit_id=audit_id,
            correlation_id=self.correlation_id,
            claim_id=claim_id,
            claim_version=version,
            state_before=state_before,
            state_after=state_after,
            action=action,
            result=result,
            error=error
        )
        
        status_msg = f"[{self.correlation_id}] Claim {claim_id} V{version} | {state_before} -> {state_after} | Action: {action}"
        if result:
            status_msg += f" | Result: {result}"
        if error:
            status_msg += f" | Error: {error}"
            
        print(status_msg)
