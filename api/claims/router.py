"""HTTP routes for the claims API boundary (Phase 5A).

Routes contain NO business logic: they parse validated request models,
delegate to ClaimService, and translate service exceptions to HTTP codes.

  POST   /api/claims                            create + process a claim
  GET    /api/claims                            list claim summaries
  GET    /api/claims/{claim_id}                 claim status + decision (full record)
  GET    /api/claims/{claim_id}/timeline        workflow audit timeline
  GET    /api/claims/{claim_id}/evidence-request  evidence request + lifecycle status
  GET    /api/claims/{claim_id}/versions        immutable version + submission history
  POST   /api/claims/{claim_id}/provider-decision provider ACCEPT/DECLINE consent
  GET    /api/claims/{claim_id}/provider-decisions decision history
  POST   /api/claims/{claim_id}/human-resolution  resolve a HUMAN_REVIEW hold
"""

from fastapi import APIRouter, FastAPI, HTTPException

from agent2.workflow.control_plane import IllegalWorkflowTransition

from .schemas import CreateClaimRequest, HumanResolutionRequest, ProviderDecisionRequest
from .service import ClaimNotFound, ClaimService


def build_claims_router(service: ClaimService) -> APIRouter:
    router = APIRouter(tags=["claims"])

    @router.post("/claims", status_code=201)
    def create_claim(payload: CreateClaimRequest):
        try:
            return service.create_claim(payload)
        except ClaimNotFound as exc:
            raise HTTPException(status_code=404, detail=f"Claim not found: {exc}")
        except IllegalWorkflowTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    @router.get("/claims")
    def list_claims():
        return service.list_claims()

    @router.get("/claims/{claim_id}")
    def get_claim(claim_id: str):
        try:
            return service.get_claim(claim_id)
        except ClaimNotFound:
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")

    @router.get("/claims/{claim_id}/timeline")
    def get_timeline(claim_id: str):
        try:
            events = service.get_timeline(claim_id)
        except ClaimNotFound:
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")
        return {"claim_id": claim_id, "events": events}

    @router.get("/claims/{claim_id}/evidence-request")
    def get_evidence_request(claim_id: str):
        try:
            erq = service.get_evidence_request(claim_id)
        except ClaimNotFound:
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")
        return {"claim_id": claim_id, "evidence_request": erq}

    @router.get("/claims/{claim_id}/versions")
    def get_versions(claim_id: str):
        try:
            return service.get_versions(claim_id)
        except ClaimNotFound:
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")

    @router.post("/claims/{claim_id}/provider-decision", status_code=201)
    def post_provider_decision(claim_id: str, payload: ProviderDecisionRequest):
        try:
            return service.record_provider_decision(
                claim_id,
                payload.decision,
                reason=payload.reason,
                evidence_ids=payload.evidence_ids,
            )
        except ClaimNotFound:
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @router.get("/claims/{claim_id}/provider-decisions")
    def get_provider_decisions(claim_id: str):
        try:
            return {
                "claim_id": claim_id,
                "provider_decisions": service.get_provider_decisions(claim_id),
            }
        except ClaimNotFound:
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")

    @router.post("/claims/{claim_id}/human-resolution")
    def post_human_resolution(claim_id: str, payload: HumanResolutionRequest):
        try:
            return service.resolve_human_review(
                claim_id,
                resolution_note=payload.resolution_note,
                attached_evidence=payload.attached_evidence,
                resolved_by=payload.resolved_by,
            )
        except ClaimNotFound:
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")
        except PermissionError as exc:
            # Phase 3: hospital-only resolution; insurance is read-only.
            raise HTTPException(status_code=403, detail=str(exc))
        except IllegalWorkflowTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    return router


def create_claims_app(service: ClaimService) -> FastAPI:
    """Standalone app exposing only the claims API (used by contract tests)."""
    app = FastAPI(
        title="CTS Claims API (V1 workflow boundary)",
        version="5.0.0",
    )
    app.include_router(build_claims_router(service), prefix="/api")
    return app
