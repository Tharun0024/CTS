"""Simulation Manager: patient lifecycle over the EXISTING V1 pipeline (Phase 5B).

The manager never implements decision logic of its own. Every simulated
patient is processed by the real Phase 5A ClaimService (which runs
services.integrated_pipeline.run_agent2_v1_pipeline on the frozen routing
contract). The manager only:

  - generates unique patients (unique patient_id per run; fresh ids on
    re-simulation),
  - persists simulation -> patient -> claim relationships,
  - processes EXACTLY ONE patient at a time (single sequential worker; a
    second concurrent run is rejected),
  - measures the actual end-to-end pipeline duration per patient and uses
    that duration to pace the next patient,
  - tracks status / current patient / completed count / timing,
  - supports start, stop, reset/delete and re-simulate, deleting ONLY the
    data belonging to the targeted simulation,
  - keeps simulated provider-side data (claims, evidence pool, documents)
    logically separated from insurer-side data (member/coverage context).
"""

import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from api.claims.schemas import CreateClaimRequest
from api.claims.service import ClaimService
from api.persistence import InMemorySimulationRepository, SimulationRepository

from .document_ingest import build_document_evidence, extract_document_text
from .generator import DefaultPatientFactory


class SimulationNotFound(KeyError):
    """Raised when an API call targets an unknown simulation_id."""


class PatientNotFound(KeyError):
    """Raised when a document upload targets an unknown simulated patient."""


class SimulationBusy(RuntimeError):
    """Raised when a run is requested while another run is still active."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SimulatedProviderStore:
    """Provider-side evidence pool for one simulation run.

    This is the ONLY data source Agent2 recovery may use for simulated
    patients; insurer-side data never enters this store.
    """

    def __init__(self):
        self._pools: Dict[str, List[Dict[str, Any]]] = {}

    def add(self, patient_id: str, items: List[Dict[str, Any]]) -> None:
        self._pools.setdefault(patient_id, []).extend(deepcopy(items))

    def pool_for(self, patient_id: str) -> List[Dict[str, Any]]:
        return [deepcopy(item) for item in self._pools.get(patient_id, [])]

    def recovery_source(self) -> Callable[..., List[Dict[str, Any]]]:
        def source(requested_keys, concepts, claim):
            patient_id = (
                claim.get("patient_id")
                or (claim.get("case_data") or {}).get("clinical_metrics", {}).get("patient_id")
            )
            return self.pool_for(patient_id) if patient_id else []

        return source


class _SimRuntime:
    """Mutable execution context owned by one simulation run."""

    def __init__(self, service: ClaimService, provider_store: SimulatedProviderStore):
        self.service = service
        self.provider_store = provider_store
        self.thread: Optional[threading.Thread] = None
        self.stop_requested = False


class SimulationManager:
    """Orchestrates simulated patient lifecycles over the real V1 pipeline."""

    def __init__(
        self,
        components: Optional[Dict[str, Any]] = None,
        simulation_store: Optional[SimulationRepository] = None,
        patient_factory: Optional[Any] = None,
        claim_service_factory: Optional[Callable[..., ClaimService]] = None,
        sleep_fn: Optional[Callable[[float], None]] = None,
        pace_multiplier: float = 1.0,
        max_pace_seconds: Optional[float] = None,
        document_store: Optional[Any] = None,
    ):
        # components may be injected later (api/main.py lifespan).
        self.components = components
        self.simulation_store = simulation_store or InMemorySimulationRepository()
        self.patient_factory = patient_factory  # None -> DefaultPatientFactory per run
        self.claim_service_factory = claim_service_factory
        self._sleep = sleep_fn or time.sleep
        self.pace_multiplier = pace_multiplier
        self.max_pace_seconds = max_pace_seconds
        # Raw document bytes store (Phase 7). None -> originals not retained
        # (extraction-only); api/main.py injects LocalFileDocumentStore.
        self.document_store = document_store

        self._lock = threading.RLock()
        self._runtimes: Dict[str, _SimRuntime] = {}
        self._issued_patient_ids: set = set()  # global uniqueness ledger

    # -- lifecycle --------------------------------------------------------------

    def start(self, request) -> Dict[str, Any]:
        if self.components is None:
            raise RuntimeError("SimulationManager components are not configured.")
        with self._lock:
            active = self._active_simulation_id()
            if active is not None:
                raise SimulationBusy(
                    f"Simulation {active} is already running; exactly one run at a time."
                )

            simulation_id = f"SIM-{uuid.uuid4().hex[:12].upper()}"
            factory = self.patient_factory or DefaultPatientFactory(policy_id=request.policy_id)
            provider_store = SimulatedProviderStore()
            service = self._build_claim_service(provider_store)

            patients_meta: List[Dict[str, Any]] = []
            payer_contexts: Dict[str, Dict[str, Any]] = {}
            for seq in range(1, request.count + 1):
                descriptor = factory.make_patient(simulation_id, seq)
                patient_id = descriptor["patient_id"]
                if patient_id in self._issued_patient_ids:
                    raise ValueError(f"Generated duplicate patient_id {patient_id}.")
                self._issued_patient_ids.add(patient_id)
                provider_store.add(patient_id, descriptor["canonical_claim"].get("evidence") or [])
                provider_store.add(patient_id, descriptor.get("provider_evidence_pool") or [])
                payer_contexts[patient_id] = descriptor["payer_context"]  # kept separate
                patients_meta.append({
                    "patient_id": patient_id,
                    "claim_id": descriptor["claim_id"],
                    "scenario": descriptor["scenario"],
                    "status": "PENDING",
                    "decision_outcome": None,
                    "decision_status": None,
                    "claim_status": None,
                    "started_at": None,
                    "completed_at": None,
                    "duration_seconds": None,
                    "documents": [],
                    "_descriptor": descriptor,
                })

            record = {
                "simulation_id": simulation_id,
                "source": request.source,
                "status": "RUNNING",
                "rerun_of": None,
                "created_at": _utc_now_iso(),
                "started_at": _utc_now_iso(),
                "completed_at": None,
                "total_count": request.count,
                "completed_count": 0,
                "failed_count": 0,
                "current_patient_id": None,
                "config": {
                    "source": request.source,
                    "count": request.count,
                    "policy_id": request.policy_id,
                    "provider_decision": request.provider_decision,
                    "max_resubmissions": request.max_resubmissions,
                    "pause_seconds": request.pause_seconds,
                },
                "timing": {
                    "last_duration_seconds": None,
                    "average_duration_seconds": None,
                    "total_duration_seconds": 0.0,
                    "last_pace_seconds": None,
                },
                "patients": patients_meta,
                "payer_contexts": payer_contexts,
                "updated_at": _utc_now_iso(),
            }
            self.simulation_store.save(record)
            runtime = _SimRuntime(service, provider_store)
            self._runtimes[simulation_id] = runtime
            runtime.thread = threading.Thread(
                target=self._run_simulation,
                args=(simulation_id, request.provider_decision, request.max_resubmissions,
                      request.pause_seconds),
                daemon=True,
                name=f"sim-{simulation_id}",
            )
            runtime.thread.start()
            return self._public_record(record)

    def stop(self, simulation_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            sim_id = simulation_id or self._active_simulation_id() or self._latest_simulation_id()
            record = self._require_record(sim_id)
            runtime = self._runtimes.get(sim_id)
            if runtime is None or runtime.thread is None or not runtime.thread.is_alive():
                return self._public_record(record)
            runtime.stop_requested = True
            record["status"] = "STOPPING"
            record["updated_at"] = _utc_now_iso()
            self.simulation_store.save(record)
            return self._public_record(record)

    def reset(self, simulation_id: Optional[str] = None) -> Dict[str, Any]:
        """Reset = stop + delete targeted simulation (or ALL simulations if none specified)."""
        with self._lock:
            if simulation_id:
                return self.delete(simulation_id)
            
            # If no simulation_id is specified, delete ALL simulations
            sim_records = self.simulation_store.list()
            sim_ids = [s.get("simulation_id") for s in sim_records if s.get("simulation_id")]
            if not sim_ids:
                raise SimulationNotFound("No simulation to reset.")
            
            deleted_counts = {
                "deleted": True,
                "simulations_deleted": len(sim_ids),
                "patients_deleted": 0,
                "claims_deleted": []
            }
            
            for sim_id in sim_ids:
                res = self.delete(sim_id)
                deleted_counts["patients_deleted"] += res.get("patients_deleted", 0)
                deleted_counts["claims_deleted"].extend(res.get("claims_deleted", []))
                
            self._issued_patient_ids.clear()
            return deleted_counts

    def delete(self, simulation_id: str) -> Dict[str, Any]:
        """Delete ONLY the patients/claims/data belonging to this simulation."""
        runtime = None
        with self._lock:
            record = self._require_record(simulation_id)
            runtime = self._runtimes.get(simulation_id)
            if runtime is not None:
                runtime.stop_requested = True
        if runtime is not None and runtime.thread is not None and runtime.thread.is_alive():
            runtime.thread.join(timeout=15)

        with self._lock:
            record = self._require_record(simulation_id)
            runtime = self._runtimes.get(simulation_id)
            deleted_claims: List[str] = []
            if runtime is not None:
                for patient in record.get("patients") or []:
                    claim_ids = [patient.get("claim_id")]
                    claim_ids.extend(doc.get("claim_id") for doc in patient.get("documents") or [])
                    for claim_id in claim_ids:
                        if claim_id and runtime.service.claim_store.delete(claim_id):
                            deleted_claims.append(claim_id)
            self.simulation_store.delete(simulation_id)
            self._runtimes.pop(simulation_id, None)
            return {
                "deleted": True,
                "simulation_id": simulation_id,
                "patients_deleted": len(record.get("patients") or []),
                "claims_deleted": deleted_claims,
            }

    def resimulate(self, simulation_id: str, count: Optional[int] = None) -> Dict[str, Any]:
        """Fresh run with the same configuration; always fresh unique ids."""
        with self._lock:
            record = self._require_record(simulation_id)
            active = self._active_simulation_id()
            if active is not None:
                raise SimulationBusy(
                    f"Simulation {active} is already running; exactly one run at a time."
                )
            config = record.get("config") or {}

        class _ResimRequest:
            pass

        request = _ResimRequest()
        request.source = config.get("source") or "re-simulation"
        request.count = count or config.get("count") or 1
        request.policy_id = config.get("policy_id")
        request.provider_decision = config.get("provider_decision") or "ACCEPT"
        request.max_resubmissions = config.get("max_resubmissions")
        request.pause_seconds = config.get("pause_seconds") or 0.0
        new_record = self.start(request)
        with self._lock:
            stored = self._require_record(new_record["simulation_id"])
            stored["rerun_of"] = simulation_id
            stored["updated_at"] = _utc_now_iso()
            self.simulation_store.save(stored)
            return self._public_record(stored)

    def service_for_claim(self, claim_id: str):
        """Locate the simulation-scoped ClaimService owning ``claim_id``.

        Returns None when no simulation run stores that claim. Used as the
        fallback locator by the main claims API so simulation claims can be
        served through the same /api/claims routes.
        """
        with self._lock:
            runtimes = list(self._runtimes.values())
        for runtime in runtimes:
            if runtime.service.claim_store.get(claim_id) is not None:
                return runtime.service
        return None

    # -- queries -----------------------------------------------------------------

    def claims(self, claim_id: Optional[str] = None) -> Any:
        """Expose simulation-scoped claim records (read-only delegation).

        Without ``claim_id``: summaries of every claim stored in any
        simulation run's ClaimService, enriched with canonical display fields
        (procedure, service date, diagnoses, payer). With ``claim_id``: the
        full live claim record from the owning simulation's ClaimService.
        The real Phase 5A service remains the source of truth; nothing here
        re-implements or alters pipeline semantics.
        """
        with self._lock:
            runtimes = [(sim_id, runtime) for sim_id, runtime in self._runtimes.items()]
        if claim_id is not None:
            for sim_id, runtime in runtimes:
                record = runtime.service.claim_store.get(claim_id)
                if record is not None:
                    enriched = runtime.service._with_live_views(record)
                    enriched["simulation_id"] = sim_id
                    return enriched
            raise SimulationNotFound(f"No simulation owns claim {claim_id}.")

        summaries: List[Dict[str, Any]] = []
        for sim_id, runtime in runtimes:
            for summary in runtime.service.list_claims():
                record = runtime.service.claim_store.get(summary["claim_id"]) or {}
                canonical = record.get("canonical_claim") or {}
                case_data = canonical.get("case_data") or {}
                metrics = case_data.get("clinical_metrics") or {}
                procedures = case_data.get("procedures") or []
                summary["simulation_id"] = sim_id
                summary["patient_id"] = record.get("patient_id") or summary.get("patient_id")
                summary["procedure"] = metrics.get("claim_procedure") or (
                    procedures[0] if procedures else None
                )
                summary["procedure_code"] = procedures[0] if procedures else None
                summary["diagnosis_codes"] = list(case_data.get("diagnoses") or [])
                summary["service_date"] = (canonical.get("submission") or {}).get("date")
                summary["payer"] = metrics.get("claim_payer")
                summary["policy_id"] = metrics.get("claim_policy_id")
                summaries.append(summary)
        return summaries

    def status(self, simulation_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            sim_id = simulation_id or self._latest_simulation_id()
            record = self._require_record(sim_id)
            return self._public_record(record)

    def list_simulations(self) -> List[Dict[str, Any]]:
        with self._lock:
            summaries = []
            for record in self.simulation_store.list():
                summaries.append({
                    "simulation_id": record.get("simulation_id"),
                    "source": record.get("source"),
                    "status": record.get("status"),
                    "rerun_of": record.get("rerun_of"),
                    "total_count": record.get("total_count"),
                    "completed_count": record.get("completed_count"),
                    "created_at": record.get("created_at"),
                    "completed_at": record.get("completed_at"),
                    "timing": record.get("timing"),
                })
            return summaries

    def wait(self, simulation_id: Optional[str] = None, timeout: float = 60.0) -> Dict[str, Any]:
        """Block until the run's worker finishes (test/determinism helper)."""
        with self._lock:
            sim_id = simulation_id or self._latest_simulation_id()
            self._require_record(sim_id)
            runtime = self._runtimes.get(sim_id)
        if runtime is not None and runtime.thread is not None:
            runtime.thread.join(timeout=timeout)
        return self.status(sim_id)

    # -- document ingestion --------------------------------------------------------

    def upload_document(
        self,
        patient_id: str,
        filename: str,
        content: bytes,
        evidence_key: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """upload -> extract -> provider-side evidence -> patient -> V1 pipeline."""
        with self._lock:
            located = self._locate_patient(patient_id)
            if located is None:
                raise PatientNotFound(patient_id)
            sim_id, patient_index = located
            record = self._require_record(sim_id)
            runtime = self._runtimes.get(sim_id)
            if runtime is None:
                raise RuntimeError(f"Simulation {sim_id} runtime is no longer available.")
            patient = record["patients"][patient_index]

        text, mode = extract_document_text(filename, content)
        document_id = f"DOC-{uuid.uuid4().hex[:12].upper()}"
        # Persist the raw bytes locally (Phase 7) before extraction feeds
        # the pipeline; the reference travels in extracted_facts only.
        storage_reference = None
        if self.document_store is not None:
            storage_reference = self.document_store.save(document_id, filename, content)
        evidence = build_document_evidence(
            document_id=document_id,
            filename=filename,
            patient_id=patient_id,
            extracted_text=text,
            extraction_mode=mode,
            evidence_key=evidence_key,
            doc_type=doc_type,
        )
        if storage_reference:
            evidence["extracted_facts"]["storage_reference"] = storage_reference
        runtime.provider_store.add(patient_id, [evidence])

        # Re-run the REAL V1 pipeline for this patient with the document
        # evidence attached (new claim id; historical runs stay immutable).
        descriptor = patient.get("_descriptor") or {}
        canonical = deepcopy(descriptor.get("canonical_claim") or {})
        doc_seq = len(patient.get("documents") or []) + 1
        canonical["claim_id"] = f"{patient['claim_id']}-DOC{doc_seq}"
        canonical.setdefault("evidence", []).append(evidence)

        started = time.perf_counter()
        claim_record = runtime.service.create_claim(CreateClaimRequest(canonical_claim=canonical))
        duration = time.perf_counter() - started

        document_entry = {
            "document_id": document_id,
            "filename": filename,
            "patient_id": patient_id,
            "evidence_id": evidence["evidence_id"],
            "evidence_key": evidence["evidence_key"],
            "provenance": evidence["extracted_facts"]["provenance"],
            "storage_reference": storage_reference,
            "extraction_mode": mode,
            "claim_id": canonical["claim_id"],
            "decision_outcome": (claim_record.get("decision") or {}).get("outcome"),
            "decision_status": (claim_record.get("decision") or {}).get("status"),
            "claim_status": claim_record.get("status"),
            "duration_seconds": round(duration, 6),
            "uploaded_at": evidence["extracted_facts"]["uploaded_at"],
        }
        with self._lock:
            record = self._require_record(sim_id)
            record["patients"][patient_index]["documents"].append(document_entry)
            record["updated_at"] = _utc_now_iso()
            self.simulation_store.save(record)
        return document_entry

    # -- worker ------------------------------------------------------------------

    def _run_simulation(
        self,
        simulation_id: str,
        provider_decision: str,
        max_resubmissions: Optional[int],
        pause_seconds: float,
    ) -> None:
        try:
            with self._lock:
                record = self._require_record(simulation_id)
                runtime = self._runtimes[simulation_id]
                total = record["total_count"]

            for index, _ in enumerate(range(total)):
                if runtime.stop_requested:
                    break
                with self._lock:
                    record = self._require_record(simulation_id)
                    patient = record["patients"][index]
                    record["current_patient_id"] = patient["patient_id"]
                    patient["status"] = "PROCESSING"
                    patient["started_at"] = _utc_now_iso()
                    record["updated_at"] = _utc_now_iso()
                    self.simulation_store.save(record)
                    descriptor = patient["_descriptor"]

                # THE real V1 pipeline (Phase 5A ClaimService) — no simulation
                # shortcuts, no second pipeline.
                started = time.perf_counter()
                error: Optional[str] = None
                claim_record: Optional[Dict[str, Any]] = None
                try:
                    claim_record = runtime.service.create_claim(
                        CreateClaimRequest(
                            canonical_claim=descriptor["canonical_claim"],
                            provider_decision=provider_decision,
                            max_resubmissions=max_resubmissions,
                        )
                    )
                except Exception as exc:  # keep the run alive; mark patient failed
                    error = str(exc)
                duration = time.perf_counter() - started

                with self._lock:
                    record = self._require_record(simulation_id)
                    patient = record["patients"][index]
                    patient["completed_at"] = _utc_now_iso()
                    patient["duration_seconds"] = round(duration, 6)
                    if claim_record is not None:
                        patient["status"] = "COMPLETED"
                        patient["claim_status"] = claim_record.get("status")
                        decision = claim_record.get("decision") or {}
                        patient["decision_outcome"] = decision.get("outcome")
                        patient["decision_status"] = decision.get("status")
                        record["completed_count"] += 1
                    else:
                        patient["status"] = "FAILED"
                        patient["error"] = error
                        record["failed_count"] += 1

                    timing = record["timing"]
                    timing["last_duration_seconds"] = round(duration, 6)
                    finished = [
                        p["duration_seconds"] for p in record["patients"]
                        if p.get("duration_seconds") is not None
                    ]
                    timing["total_duration_seconds"] = round(sum(finished), 6)
                    timing["average_duration_seconds"] = (
                        round(sum(finished) / len(finished), 6) if finished else None
                    )
                    record["updated_at"] = _utc_now_iso()
                    self.simulation_store.save(record)

                # Duration-based pacing: the measured end-to-end duration of
                # this patient paces the generation/processing of the next one.
                if index < total - 1 and not runtime.stop_requested:
                    pace = duration * self.pace_multiplier
                    if self.max_pace_seconds is not None:
                        pace = min(pace, self.max_pace_seconds)
                    pace = max(pace, pause_seconds or 0.0)
                    with self._lock:
                        record = self._require_record(simulation_id)
                        record["timing"]["last_pace_seconds"] = round(pace, 6)
                        self.simulation_store.save(record)
                    self._sleep(pace)

            with self._lock:
                record = self._require_record(simulation_id)
                record["status"] = "STOPPED" if runtime.stop_requested else "COMPLETED"
                record["current_patient_id"] = None
                record["completed_at"] = _utc_now_iso()
                record["updated_at"] = _utc_now_iso()
                self.simulation_store.save(record)
        except Exception as exc:  # catastrophic: never leave the run dangling
            with self._lock:
                try:
                    record = self._require_record(simulation_id)
                    record["status"] = "FAILED"
                    record["error"] = str(exc)
                    record["updated_at"] = _utc_now_iso()
                    self.simulation_store.save(record)
                except SimulationNotFound:
                    pass

    # -- internals -----------------------------------------------------------------

    def _build_claim_service(self, provider_store: SimulatedProviderStore) -> ClaimService:
        if self.claim_service_factory is not None:
            return self.claim_service_factory(self.components, provider_store.recovery_source())
        # Same ClaimService class as the live claims API: same pipeline, same
        # routing contract — only the data scope is simulation-local.
        return ClaimService(
            components=self.components,
            recovery_source=provider_store.recovery_source(),
        )

    def _require_record(self, simulation_id: Optional[str]) -> Dict[str, Any]:
        if not simulation_id:
            raise SimulationNotFound("No simulation_id provided.")
        record = self.simulation_store.get(simulation_id)
        if record is None:
            raise SimulationNotFound(simulation_id)
        return record

    def _active_simulation_id(self) -> Optional[str]:
        for sim_id, runtime in self._runtimes.items():
            if runtime.thread is not None and runtime.thread.is_alive():
                return sim_id
        return None

    def _latest_simulation_id(self) -> Optional[str]:
        records = self.simulation_store.list()  # newest created_at first
        return records[0]["simulation_id"] if records else None

    def _locate_patient(self, patient_id: str) -> Optional[tuple]:
        for record in self.simulation_store.list():
            for index, patient in enumerate(record.get("patients") or []):
                if patient.get("patient_id") == patient_id:
                    return record["simulation_id"], index
        return None

    @staticmethod
    def _public_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Strip internal descriptor payloads from API-facing records."""
        public = dict(record)
        public["patients"] = [
            {k: v for k, v in patient.items() if not k.startswith("_")}
            for patient in record.get("patients") or []
        ]
        return public
