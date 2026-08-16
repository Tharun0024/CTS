"""Phase 5B contract tests: Simulation Manager + document ingestion.

Covers: unique patients, one-at-a-time processing, duration-based pacing,
simulation stop/reset/delete, re-simulation with fresh ids, isolation from
other simulations' data, provider/insurer separation, document extraction +
provenance, and pipeline reuse (every simulated patient runs through the
real Phase 5A ClaimService / run_agent2_v1_pipeline — no second pipeline).
"""

import base64
import threading
import time

import pytest
from fastapi.testclient import TestClient

from adapters.rag_adapter import CRITERIA_RULES_REGISTRY
from api.claims.service import ClaimService
from api.simulation import (
    DefaultPatientFactory,
    PatientNotFound,
    SimulationBusy,
    SimulationManager,
    SimulationNotFound,
    StartSimulationRequest,
    build_document_evidence,
    create_simulation_app,
    extract_document_text,
)
from tests.test_agent2_v1_end_to_end import _build_components, _chunk, _ev


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------

SIM_POLICY = "POL-SIM-KNEE"
SIM_CRITERION = "C-SIM-PT"


@pytest.fixture
def sim_registry(monkeypatch):
    monkeypatch.setitem(
        CRITERIA_RULES_REGISTRY,
        (SIM_POLICY, SIM_CRITERION),
        {
            "required_evidence_keys": ["conservative_treatment"],
            "clinical_rule": {
                "field": "clinical_metrics.pt_weeks_completed",
                "operator": "gte",
                "value": 12,
            },
            "evidence_rule": None,
        },
    )


def _sim_chunks():
    return [
        _chunk(
            SIM_POLICY,
            SIM_CRITERION,
            "At least 12 weeks of conservative treatment such as physical therapy required.",
        )
    ]


class _RegistryPatientFactory:
    """Deterministic test factory producing registry-compatible patients."""

    def __init__(self, scenarios):
        self.scenarios = list(scenarios)

    def make_patient(self, simulation_id, seq):
        scenario = self.scenarios[(seq - 1) % len(self.scenarios)]
        patient_id = f"PAT-{simulation_id}-{seq:04d}"
        claim_id = f"CLM-{patient_id}"
        metrics = {
            "patient_gender": "Female",
            "claim_scenario_type": scenario,
            "claim_payer": "Aetna",
            "claim_policy_id": SIM_POLICY,
        }
        evidence = [_ev("diagnosis", f"EV-{patient_id}-DX", {"verified_facts": True})]
        pool = []
        if scenario == "COMPLETE":
            metrics["pt_weeks_completed"] = 16
            evidence.append(
                _ev("conservative_treatment", f"EV-{patient_id}-PT", {"pt_weeks_completed": 16})
            )
        elif scenario == "MISSING":
            # Absent at submission, present provider-side -> Agent2 recovery.
            pool.append(
                _ev("conservative_treatment", f"EV-{patient_id}-PT", {"pt_weeks_completed": 16})
            )
        else:  # NOT_SATISFIED
            metrics["pt_weeks_completed"] = 4
            evidence.append(
                _ev("conservative_treatment", f"EV-{patient_id}-PT", {"pt_weeks_completed": 4})
            )
        canonical_claim = {
            "claim_id": claim_id,
            "patient_id": patient_id,
            "submission": {"attempt": 1, "date": "2026-08-16T00:00:00Z"},
            "case_data": {
                "case_id": claim_id,
                "patient_age": 55,
                "diagnoses": ["M17.11"],
                "procedures": ["27447"],
                "clinical_metrics": metrics,
            },
            "evidence": evidence,
        }
        return {
            "patient_id": patient_id,
            "claim_id": claim_id,
            "age": 55,
            "gender": "Female",
            "scenario": scenario,
            "canonical_claim": canonical_claim,
            "provider_evidence_pool": pool,
            "payer_context": {
                "member_id": f"MEM-{simulation_id}-{seq:04d}",
                "patient_id": patient_id,
                "payer_id": "Aetna",
                "plan_id": "PLAN-AETNA-SIM",
                "coverage_status": "ACTIVE",
            },
        }


class HookedClaimService(ClaimService):
    """Real ClaimService with test hooks around create_claim (timing/gating)."""

    def __init__(self, hooks, **kwargs):
        super().__init__(**kwargs)
        self._hooks = hooks

    def create_claim(self, request):
        for hook in self._hooks:
            hook(request)
        return super().create_claim(request)


def _hooked_factory(hooks):
    def factory(components, recovery_source):
        return HookedClaimService(
            hooks, components=components, recovery_source=recovery_source
        )

    return factory


def _make_manager(factory, hooks=None, sleep_fn=None, **kwargs):
    return SimulationManager(
        components=_build_components(_sim_chunks()),
        patient_factory=factory,
        claim_service_factory=_hooked_factory(hooks or []),
        sleep_fn=sleep_fn,
        **kwargs,
    )


def _request(count, **overrides):
    payload = {"source": "Phase 5B contract test", "count": count}
    payload.update(overrides)
    return StartSimulationRequest(**payload)


def _wait_until(predicate, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


# ---------------------------------------------------------------------------
# Unique patients + fresh ids on new runs / re-simulation
# ---------------------------------------------------------------------------

class TestUniquePatientsAndFreshRuns:
    def test_patient_ids_unique_within_and_across_runs(self, sim_registry):
        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        first = manager.start(_request(3))
        manager.wait(first["simulation_id"])
        second = manager.start(_request(3))
        manager.wait(second["simulation_id"])

        ids_a = [p["patient_id"] for p in manager.status(first["simulation_id"])["patients"]]
        ids_b = [p["patient_id"] for p in manager.status(second["simulation_id"])["patients"]]
        assert len(set(ids_a)) == 3
        assert len(set(ids_b)) == 3
        assert set(ids_a).isdisjoint(set(ids_b))
        assert first["simulation_id"] != second["simulation_id"]

    def test_resimulation_generates_fresh_unique_ids(self, sim_registry):
        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        original = manager.start(_request(2))
        manager.wait(original["simulation_id"])

        rerun = manager.resimulate(original["simulation_id"])
        manager.wait(rerun["simulation_id"])

        assert rerun["simulation_id"] != original["simulation_id"]
        assert rerun["rerun_of"] == original["simulation_id"]
        original_ids = {p["patient_id"] for p in manager.status(original["simulation_id"])["patients"]}
        rerun_ids = {p["patient_id"] for p in manager.status(rerun["simulation_id"])["patients"]}
        assert rerun_ids and original_ids.isdisjoint(rerun_ids)

    def test_default_factory_ids_are_run_scoped(self):
        factory = DefaultPatientFactory(policy_id="POL-X")
        one = factory.make_patient("SIM-AAAA", 1)
        two = factory.make_patient("SIM-BBBB", 1)
        assert one["patient_id"] != two["patient_id"]
        assert one["patient_id"].startswith("PAT-SIM-AAAA-")
        assert one["claim_id"] == f"CLM-{one['patient_id']}"


# ---------------------------------------------------------------------------
# One-at-a-time processing + duration-based pacing
# ---------------------------------------------------------------------------

class TestOneAtATimeAndPacing:
    def test_concurrent_start_rejected_while_running(self, sim_registry):
        gate = threading.Event()
        manager = _make_manager(
            _RegistryPatientFactory(["COMPLETE"]),
            hooks=[lambda request: gate.wait(timeout=10)],
        )
        try:
            manager.start(_request(1))
            assert _wait_until(lambda: manager.status()["status"] == "RUNNING")
            with pytest.raises(SimulationBusy):
                manager.start(_request(1))
        finally:
            gate.set()
        final = manager.wait()
        assert final["status"] == "COMPLETED"

    def test_exactly_one_patient_processed_at_a_time(self, sim_registry):
        in_flight = []
        max_concurrent = {"value": 0}
        lock = threading.Lock()

        def hook(request):
            with lock:
                in_flight.append(request)
                max_concurrent["value"] = max(max_concurrent["value"], len(in_flight))
            time.sleep(0.02)
            with lock:
                in_flight.pop()

        manager = _make_manager(
            _RegistryPatientFactory(["COMPLETE"]), hooks=[hook]
        )
        manager.start(_request(4))
        final = manager.wait()
        assert final["completed_count"] == 4
        assert max_concurrent["value"] == 1  # never two pipelines at once

    def test_next_patient_paced_by_measured_duration(self, sim_registry):
        slept = []
        hooks = [lambda request: time.sleep(0.05)]  # measurable pipeline work

        manager = _make_manager(
            _RegistryPatientFactory(["COMPLETE"]),
            hooks=hooks,
            sleep_fn=lambda seconds: slept.append(seconds),
        )
        manager.start(_request(3))
        final = manager.wait()

        durations = [p["duration_seconds"] for p in final["patients"]]
        assert len(slept) == 2  # pacing only BETWEEN patients
        assert durations[0] >= 0.05  # actual end-to-end duration measured
        for pace, duration in zip(slept, durations):
            assert pace == pytest.approx(duration, abs=1e-5)
        assert final["timing"]["last_pace_seconds"] == pytest.approx(slept[-1], abs=1e-5)
        assert final["timing"]["total_duration_seconds"] > 0
        assert final["timing"]["average_duration_seconds"] > 0

    def test_status_tracks_progress_and_timing(self, sim_registry):
        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        manager.start(_request(2))
        final = manager.wait()
        assert final["status"] == "COMPLETED"
        assert final["completed_count"] == final["total_count"] == 2
        assert final["current_patient_id"] is None
        assert final["completed_at"] is not None
        for patient in final["patients"]:
            assert patient["status"] == "COMPLETED"
            assert patient["duration_seconds"] > 0
            assert patient["started_at"] and patient["completed_at"]


# ---------------------------------------------------------------------------
# Lifecycle: stop / reset / delete / re-simulate + pipeline reuse
# ---------------------------------------------------------------------------

class TestLifecycleAndPipelineReuse:
    def test_stop_halts_before_remaining_patients(self, sim_registry):
        second_gate = threading.Event()
        calls = {"n": 0}
        calls_lock = threading.Lock()

        def gate_second(request):
            with calls_lock:
                calls["n"] += 1
                n = calls["n"]
            if n == 2:
                second_gate.wait(timeout=10)

        manager = _make_manager(
            _RegistryPatientFactory(["COMPLETE"]), hooks=[gate_second]
        )
        record = manager.start(_request(3))
        sim_id = record["simulation_id"]
        blocked_patient = record["patients"][1]["patient_id"]
        assert _wait_until(
            lambda: manager.status(sim_id)["current_patient_id"] == blocked_patient
        )
        stopped = manager.stop(sim_id)
        assert stopped["status"] == "STOPPING"
        second_gate.set()

        final = manager.wait(sim_id)
        assert final["status"] == "STOPPED"
        assert final["completed_count"] == 2
        assert final["patients"][2]["status"] == "PENDING"

    def test_pipeline_reuse_real_claim_records(self, sim_registry):
        manager = _make_manager(
            _RegistryPatientFactory(["COMPLETE", "MISSING", "NOT_SATISFIED"])
        )
        record = manager.start(_request(3))
        final = manager.wait(record["simulation_id"])
        patients = final["patients"]

        # COMPLETE: real Agent1 APPROVE, terminal, no Agent2.
        assert patients[0]["decision_outcome"] == "APPROVE"
        assert patients[0]["claim_status"] == "ACCEPTED"
        # MISSING: real RMI -> Agent2 recovery -> V2 re-evaluation.
        assert patients[1]["decision_outcome"] == "APPROVE"
        assert patients[1]["claim_status"] == "ACCEPTED"
        # NOT_SATISFIED: real terminal REJECT.
        assert patients[2]["decision_outcome"] == "REJECT"
        assert patients[2]["claim_status"] == "REJECTED"

        # The records live in a REAL ClaimService store (Phase 5A contract):
        runtime = manager._runtimes[record["simulation_id"]]
        missing_claim = runtime.service.claim_store.get(patients[1]["claim_id"])
        assert missing_claim is not None
        assert missing_claim["agent2_invoked"] is True
        assert missing_claim["resubmissions"] == 1
        assert [v["version"] for v in missing_claim["versions"]] == ["V1", "V2"]
        assert missing_claim["timeline"]  # control-plane audit trail present

    def test_delete_removes_only_that_simulations_data(self, sim_registry):
        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        run_a = manager.start(_request(2))
        manager.wait(run_a["simulation_id"])
        run_b = manager.start(_request(1))
        manager.wait(run_b["simulation_id"])

        result = manager.delete(run_a["simulation_id"])
        assert result["deleted"] is True
        assert result["patients_deleted"] == 2
        assert set(result["claims_deleted"]) == {
            p["claim_id"] for p in run_a["patients"]
        }

        # Simulation A is gone; simulation B is untouched.
        with pytest.raises(SimulationNotFound):
            manager.status(run_a["simulation_id"])
        remaining = manager.status(run_b["simulation_id"])
        assert remaining["completed_count"] == 1
        runtime_b = manager._runtimes[run_b["simulation_id"]]
        assert runtime_b.service.claim_store.get(run_b["patients"][0]["claim_id"]) is not None
        assert run_a["simulation_id"] not in manager._runtimes

    def test_reset_deletes_latest_simulation(self, sim_registry):
        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        manager.start(_request(1))
        manager.wait()
        result = manager.reset()
        assert result["deleted"] is True
        assert manager.list_simulations() == []
        with pytest.raises(SimulationNotFound):
            manager.reset()


# ---------------------------------------------------------------------------
# Provider / insurer separation + isolation
# ---------------------------------------------------------------------------

class TestProviderInsurerSeparation:
    def test_payer_context_kept_separate_from_provider_pool(self, sim_registry):
        manager = _make_manager(_RegistryPatientFactory(["MISSING"]))
        record = manager.start(_request(1))
        final = manager.wait(record["simulation_id"])
        patient = final["patients"][0]

        payer = final["payer_contexts"][patient["patient_id"]]
        assert payer["member_id"].startswith("MEM-")

        runtime = manager._runtimes[record["simulation_id"]]
        pool = runtime.provider_store.pool_for(patient["patient_id"])
        assert pool, "provider-side recovery pool must not be empty"
        for item in pool:
            facts = item.get("extracted_facts") or {}
            assert "member_id" not in facts
            assert payer["member_id"] not in str(item)

        # The canonical claim processed by the pipeline carries no payer data.
        claim_record = runtime.service.claim_store.get(patient["claim_id"])
        canonical = claim_record["canonical_claim"]
        assert "payer_context" not in canonical
        assert payer["member_id"] not in str(canonical)

    def test_recovery_pool_isolated_between_patients(self, sim_registry):
        manager = _make_manager(_RegistryPatientFactory(["MISSING"]))
        record = manager.start(_request(2))
        manager.wait(record["simulation_id"])
        runtime = manager._runtimes[record["simulation_id"]]
        first, second = record["patients"]
        pool_first = runtime.provider_store.pool_for(first["patient_id"])
        second_ids = {item["evidence_id"] for item in
                      runtime.provider_store.pool_for(second["patient_id"])}
        assert all(item["evidence_id"] not in second_ids for item in pool_first)


# ---------------------------------------------------------------------------
# Document ingestion: extraction, provenance, pipeline reuse
# ---------------------------------------------------------------------------

class TestDocumentIngestion:
    def test_text_extraction(self):
        text, mode = extract_document_text("note.txt", b"PT progress: 20 weeks completed.")
        assert mode == "text"
        assert "20 weeks" in text

    def test_pdf_text_extraction(self):
        pdf = b"%PDF-1.4\nBT /F1 12 Tf (LVEF 30 percent documented) Tj ET\n%%EOF"
        text, mode = extract_document_text("echo.pdf", pdf)
        assert mode == "pdf"
        assert "LVEF 30 percent documented" in text

    def test_empty_content_fails_closed(self):
        text, mode = extract_document_text("blank.bin", b"\x00\x01\x02")
        assert mode == "empty"
        evidence = build_document_evidence("DOC-1", "blank.bin", "PAT-1", text, mode)
        assert evidence["extracted_facts"]["content_reference"].startswith("No extractable")
        assert evidence["extracted_facts"]["provenance"] == "DOC:DOC-1:blank.bin"

    def test_upload_creates_provenanced_evidence_and_runs_real_pipeline(self, sim_registry):
        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        record = manager.start(_request(1))
        manager.wait(record["simulation_id"])
        patient_id = record["patients"][0]["patient_id"]

        content = b"Physical therapy progress note: 20 weeks of PT completed."
        result = manager.upload_document(
            patient_id=patient_id,
            filename="pt_progress.txt",
            content=content,
            evidence_key="conservative_treatment",
        )

        assert result["provenance"].startswith("DOC:")
        assert result["provenance"].endswith(":pt_progress.txt")
        assert result["evidence_id"].endswith("-EV1")
        assert result["claim_id"].startswith(record["patients"][0]["claim_id"])
        assert result["decision_outcome"] == "APPROVE"  # real pipeline decision
        assert result["duration_seconds"] > 0

        # Provenance + document lineage persisted on the patient record.
        final = manager.status(record["simulation_id"])
        documents = final["patients"][0]["documents"]
        assert len(documents) == 1
        assert documents[0]["document_id"] == result["document_id"]

        # The document evidence actually entered the real pipeline run.
        runtime = manager._runtimes[record["simulation_id"]]
        doc_claim = runtime.service.claim_store.get(result["claim_id"])
        assert doc_claim is not None
        latest_version = doc_claim["versions"][-1]
        assert result["evidence_id"] in latest_version["evidence_ids"]
        assert doc_claim["decision"]["outcome"] == "APPROVE"

    def test_upload_unknown_patient_raises(self, sim_registry):
        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        with pytest.raises(PatientNotFound):
            manager.upload_document("PAT-NOPE", "x.txt", b"data")


# ---------------------------------------------------------------------------
# HTTP contract (routes stay logic-free; delegation + status codes)
# ---------------------------------------------------------------------------

class TestSimulationHTTPContract:
    def _client(self, factory=None, hooks=None):
        manager = _make_manager(factory or _RegistryPatientFactory(["COMPLETE"]), hooks=hooks)
        return TestClient(create_simulation_app(manager)), manager

    def test_start_status_stop_flow(self, sim_registry):
        client, manager = self._client()
        response = client.post(
            "/api/simulation/start", json={"source": "CMS", "count": 2}
        )
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["simulation_id"] == body["run_id"]
        manager.wait(body["simulation_id"])

        status = client.get("/api/simulation/status")
        assert status.status_code == 200
        assert status.json()["status"] == "COMPLETED"

        listing = client.get("/api/simulation")
        assert [s["simulation_id"] for s in listing.json()] == [body["simulation_id"]]

        stopped = client.post("/api/simulation/stop")
        assert stopped.status_code == 200

    def test_busy_returns_409(self, sim_registry):
        gate = threading.Event()
        client, manager = self._client(hooks=[lambda request: gate.wait(timeout=10)])
        try:
            assert client.post(
                "/api/simulation/start", json={"count": 1}
            ).status_code == 201
            assert _wait_until(lambda: manager.status()["status"] == "RUNNING")
            assert client.post(
                "/api/simulation/start", json={"count": 1}
            ).status_code == 409
        finally:
            gate.set()
        manager.wait()

    def test_delete_and_not_found(self, sim_registry):
        client, manager = self._client()
        started = client.post("/api/simulation/start", json={"count": 1}).json()
        manager.wait(started["simulation_id"])

        deleted = client.delete(f"/api/simulation/{started['simulation_id']}")
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True
        assert client.get("/api/simulation/status").status_code == 404
        assert client.delete("/api/simulation/SIM-NOPE").status_code == 404
        assert client.get("/api/simulation/status?simulation_id=SIM-NOPE").status_code == 404

    def test_resimulate_endpoint(self, sim_registry):
        client, manager = self._client()
        started = client.post("/api/simulation/start", json={"count": 1}).json()
        manager.wait(started["simulation_id"])

        rerun = client.post(f"/api/simulation/{started['simulation_id']}/resimulate")
        assert rerun.status_code == 201
        assert rerun.json()["rerun_of"] == started["simulation_id"]
        manager.wait(rerun.json()["simulation_id"])
        assert client.post("/api/simulation/SIM-NOPE/resimulate").status_code == 404

    def test_document_upload_endpoint(self, sim_registry):
        client, manager = self._client()
        started = client.post("/api/simulation/start", json={"count": 1}).json()
        manager.wait(started["simulation_id"])
        patient_id = manager.status()["patients"][0]["patient_id"]

        payload = {
            "patient_id": patient_id,
            "filename": "pt_note.txt",
            "content_b64": base64.b64encode(b"PT note: 20 weeks completed.").decode(),
            "evidence_key": "conservative_treatment",
        }
        response = client.post("/api/simulation/documents", json=payload)
        assert response.status_code == 201
        assert response.json()["provenance"].startswith("DOC:")

        bad_b64 = dict(payload, content_b64="***")
        assert client.post("/api/simulation/documents", json=bad_b64).status_code == 422
        unknown = dict(payload, patient_id="PAT-NOPE", content_b64=base64.b64encode(b"x").decode())
        assert client.post("/api/simulation/documents", json=unknown).status_code == 404


# ---------------------------------------------------------------------------
# Simulation-scoped claim exposure (Phase 6 frontend boundary)
# ---------------------------------------------------------------------------

class TestSimulationClaimsExposure:
    def _client(self, factory=None):
        manager = _make_manager(factory or _RegistryPatientFactory(["COMPLETE", "MISSING"]))
        return TestClient(create_simulation_app(manager)), manager

    def test_summaries_across_runs(self, sim_registry):
        client, manager = self._client()
        started = client.post("/api/simulation/start", json={"count": 2}).json()
        manager.wait(started["simulation_id"])

        response = client.get("/api/simulation/claims")
        assert response.status_code == 200
        summaries = response.json()
        assert len(summaries) == 2
        for summary in summaries:
            assert summary["simulation_id"] == started["simulation_id"]
            assert summary["patient_id"].startswith("PAT-")
            assert summary["procedure_code"] == "27447"
            assert summary["diagnosis_codes"] == ["M17.11"]
            assert summary["policy_id"] == SIM_POLICY

    def test_full_record_by_claim_id(self, sim_registry):
        client, manager = self._client()
        started = client.post("/api/simulation/start", json={"count": 1}).json()
        manager.wait(started["simulation_id"])
        patient = manager.status()["patients"][0]

        response = client.get(
            "/api/simulation/claims", params={"claim_id": patient["claim_id"]}
        )
        assert response.status_code == 200
        record = response.json()
        assert record["claim_id"] == patient["claim_id"]
        assert record["simulation_id"] == started["simulation_id"]
        # Full live claim record from the owning simulation's ClaimService.
        assert record["decision"]["outcome"] == "APPROVE"
        assert record["workflow_state"] == "APPROVED"
        assert record["canonical_claim"]["patient_id"] == patient["patient_id"]
        assert [event["action"] for event in record["timeline"]]

    def test_unknown_claim_returns_404(self, sim_registry):
        client, manager = self._client()
        started = client.post("/api/simulation/start", json={"count": 1}).json()
        manager.wait(started["simulation_id"])
        assert client.get(
            "/api/simulation/claims", params={"claim_id": "CLM-NOPE"}
        ).status_code == 404

    def test_empty_when_no_simulations(self, sim_registry):
        client, _manager = self._client()
        assert client.get("/api/simulation/claims").json() == []
        assert client.get(
            "/api/simulation/claims", params={"claim_id": "CLM-NOPE"}
        ).status_code == 404


# ---------------------------------------------------------------------------
# Local-first document storage (Phase 7; cloud-swappable DocumentStore)
# ---------------------------------------------------------------------------

class TestLocalDocumentStorage:
    def test_upload_persists_raw_bytes_locally(self, sim_registry, tmp_path):
        from api.persistence.document_store import LocalFileDocumentStore

        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        manager.document_store = LocalFileDocumentStore(root=str(tmp_path))
        record = manager.start(_request(1))
        manager.wait(record["simulation_id"])
        patient_id = manager.status()["patients"][0]["patient_id"]

        content = b"PT note: 20 weeks of physical therapy completed."
        entry = manager.upload_document(patient_id, "pt note.txt", content)
        assert entry["provenance"].startswith("DOC:")
        assert entry["storage_reference"].startswith("LOCAL:")
        # Raw bytes round-trip through the local store.
        assert manager.document_store.load(entry["storage_reference"]) == content
        # The evidence carries the storage reference; semantics unchanged.
        claim = manager.claims(entry["claim_id"])
        doc_evidence = [
            item
            for item in claim["canonical_claim"]["evidence"]
            if item["evidence_key"] == entry["evidence_key"]
        ]
        assert doc_evidence[0]["extracted_facts"]["storage_reference"] == entry["storage_reference"]

    def test_upload_without_store_keeps_extraction_only(self, sim_registry):
        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        record = manager.start(_request(1))
        manager.wait(record["simulation_id"])
        patient_id = manager.status()["patients"][0]["patient_id"]

        entry = manager.upload_document(patient_id, "note.txt", b"plain text")
        assert entry["storage_reference"] is None


# ---------------------------------------------------------------------------
# Main claims API serves simulation-scoped claims via the service locator
# (Phase 7: frontend review queue merges both sources; human resolution and
# sub-resources must not 404 for simulation claims)
# ---------------------------------------------------------------------------

class TestSimulationClaimsViaMainClaimsApi:
    def test_main_claims_routes_serve_simulation_claims(self, sim_registry):
        from api.claims import create_claims_app

        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        started = manager.start(_request(1))
        manager.wait(started["simulation_id"])
        claim_id = manager.status()["patients"][0]["claim_id"]

        main_service = ClaimService(simulation_service_locator=manager.service_for_claim)
        client = TestClient(create_claims_app(main_service))

        response = client.get(f"/api/claims/{claim_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["claim_id"] == claim_id
        assert body["decision"]["outcome"] == "APPROVE"

        timeline = client.get(f"/api/claims/{claim_id}/timeline")
        assert timeline.status_code == 200
        assert timeline.json()["events"]

        versions = client.get(f"/api/claims/{claim_id}/versions")
        assert versions.status_code == 200
        assert versions.json()["versions"]

        decisions = client.get(f"/api/claims/{claim_id}/provider-decisions")
        assert decisions.status_code == 200

    def test_locator_does_not_mask_unknown_claims(self, sim_registry):
        from api.claims import create_claims_app

        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        main_service = ClaimService(simulation_service_locator=manager.service_for_claim)
        client = TestClient(create_claims_app(main_service))
        assert client.get("/api/claims/CLM-NOPE").status_code == 404

    def test_without_locator_simulation_claims_stay_404(self, sim_registry):
        from api.claims import create_claims_app

        manager = _make_manager(_RegistryPatientFactory(["COMPLETE"]))
        started = manager.start(_request(1))
        manager.wait(started["simulation_id"])
        claim_id = manager.status()["patients"][0]["claim_id"]

        client = TestClient(create_claims_app(ClaimService()))
        assert client.get(f"/api/claims/{claim_id}").status_code == 404
