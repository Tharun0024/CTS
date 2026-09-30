"""Agent 2: Provider-Side Prior Authorization Orchestrator (V1)

Agent 2 is the provider-side orchestrator for deterministic prior authorization workflows.
It manages:
- Clinical evidence retrieval and ranking
- Policy criterion evaluation via LLM mapping
- Submission package building (minimum-necessary principle)
- Recovery routing for MORE_INFO and REJECT outcomes
- Audit logging and version management
- Trust boundary enforcement (no direct payer DB access)

Agent 2 interfaces with Agent 1 (Payer Decision Engine) via SubmissionPackage and PayerResponse
following the frozen V1 architecture.
"""

__version__ = "1.0.0"
__all__ = [
    "workflow",
    "schemas",
    "database",
    "retrieval",
    "reasoning",
    "submission",
    "payer",
    "audit",
    "validators",
    "recovery",
]
