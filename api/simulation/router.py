"""HTTP routes for the simulation + document ingestion API (Phase 5B).

Routes contain NO business logic: they parse validated request models,
delegate to SimulationManager, and translate service exceptions to HTTP
codes. The frontend never touches databases; everything flows through these
endpoints and the repository interfaces.

  POST   /api/simulation/start                     start a run (frontend contract)
  GET    /api/simulation/status                    run status / current patient / timing
  GET    /api/simulation                           all run summaries
  POST   /api/simulation/stop                      stop the active run
  POST   /api/simulation/reset                     reset (delete) targeted/latest run
  DELETE /api/simulation/{simulation_id}           delete only that run's data
  POST   /api/simulation/{simulation_id}/resimulate  fresh run, fresh unique ids
  POST   /api/simulation/documents                 upload -> extract -> evidence -> pipeline
"""

import base64
import binascii

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel

from .manager import PatientNotFound, SimulationBusy, SimulationManager, SimulationNotFound
from .schemas import ReSimulateRequest, StartSimulationRequest


class DocumentUploadRequest(BaseModel):
    """Document upload payload (content is base64-encoded file bytes)."""

    patient_id: str
    filename: str
    content_b64: str
    evidence_key: str = None
    doc_type: str = None


def build_simulation_router(manager: SimulationManager) -> APIRouter:
    router = APIRouter(tags=["simulation"])

    @router.post("/simulation/start", status_code=201)
    def start_simulation(payload: StartSimulationRequest):
        try:
            record = manager.start(payload)
        except SimulationBusy as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        return {
            "success": True,
            "message": (
                f"V1 simulation {record['simulation_id']} started: "
                f"{record['total_count']} simulated patient(s), one at a time, "
                "through the real V1 pipeline."
            ),
            "simulation_id": record["simulation_id"],
            "run_id": record["simulation_id"],  # frontend contract alias
        }

    @router.get("/simulation/status")
    def simulation_status(simulation_id: str = None):
        try:
            return manager.status(simulation_id)
        except SimulationNotFound:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")

    @router.get("/simulation")
    def list_simulations():
        return manager.list_simulations()

    @router.post("/simulation/stop")
    def stop_simulation(simulation_id: str = None):
        try:
            return manager.stop(simulation_id)
        except SimulationNotFound:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")

    @router.post("/simulation/reset")
    def reset_simulation(simulation_id: str = None):
        try:
            return manager.reset(simulation_id)
        except SimulationNotFound:
            raise HTTPException(status_code=404, detail="No simulation to reset.")

    @router.get("/simulation/claims")
    def simulation_claims(claim_id: str = None):
        """Read-only view of simulation-scoped claims.

        Without ``claim_id``: summaries across all simulation runs (frontend
        claims listing). With ``claim_id``: the full live claim record from
        the owning simulation's real ClaimService.
        """
        try:
            return manager.claims(claim_id)
        except SimulationNotFound:
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")

    @router.delete("/simulation/{simulation_id}")
    def delete_simulation(simulation_id: str):
        try:
            return manager.delete(simulation_id)
        except SimulationNotFound:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")

    @router.post("/simulation/{simulation_id}/resimulate", status_code=201)
    def resimulate(simulation_id: str, payload: ReSimulateRequest = None):
        try:
            return manager.resimulate(simulation_id, count=payload.count if payload else None)
        except SimulationNotFound:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
        except SimulationBusy as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    @router.post("/simulation/documents", status_code=201)
    def upload_document(payload: DocumentUploadRequest):
        try:
            content = base64.b64decode(payload.content_b64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(status_code=422, detail="content_b64 is not valid base64.")
        try:
            return manager.upload_document(
                patient_id=payload.patient_id,
                filename=payload.filename,
                content=content,
                evidence_key=payload.evidence_key,
                doc_type=payload.doc_type,
            )
        except PatientNotFound:
            raise HTTPException(
                status_code=404, detail=f"Simulated patient not found: {payload.patient_id}"
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    return router


def create_simulation_app(manager: SimulationManager) -> FastAPI:
    """Standalone app exposing only the simulation API (used by contract tests)."""
    app = FastAPI(
        title="CTS Simulation API (V1 patient lifecycle boundary)",
        version="5.1.0",
    )
    app.include_router(build_simulation_router(manager), prefix="/api")
    return app
