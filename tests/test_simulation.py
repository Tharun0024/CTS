"""
Test Suite for CTS V1 Simulation Framework (Supports both unittest and pytest)
"""
import unittest
import os
import sqlite3
import tempfile
import shutil
from simulation.scenarios import generate_8_scenarios
from simulation.validator import validate_all_scenarios, validate_db_table_columns, EXPECTED_PATIENT_DB_SCHEMAS, EXPECTED_PAYER_DB_SCHEMAS
from simulation.linkage import create_patient_payer_linkage, load_rag_policy_dataset, retrieve_policy_from_rag, RAGRetrievalError
from simulation.evidence import create_evidence
from simulation.resubmissions import create_resubmission_sequence, evaluate_policy_criteria_against_evidence
from simulation.adapter import build_canonical_claim_from_sqlite, build_payer_decision_context_from_sqlite
from simulation.export import export_deliverables
from simulation.db_patient import get_patient_db_tables, init_patient_db
from simulation.db_payer import get_payer_db_tables, init_payer_db


class TestCTSV1Simulation(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_generate_8_scenarios_count(self):
        scenarios = generate_8_scenarios()
        self.assertEqual(len(scenarios), 8)

    def test_validation_suite_passes(self):
        out_dir = os.path.join(self.tmp_dir, "DATA-VERSION1")
        export_deliverables(out_dir)
        scenarios = generate_8_scenarios()
        report = validate_all_scenarios(scenarios, out_dir)
        self.assertTrue(report["all_checks_passed"])
        self.assertTrue(report["total_checks_executed"] > 100)
        self.assertFalse(report["cross_patient_contamination"])
        self.assertTrue(report["resubmission_identity_preserved"])
        self.assertTrue(report["criteria_evaluation_verified"])

    def test_missing_kl_grade_returns_request_more_info(self):
        # Evidence with PT 8 weeks and Imaging, but missing KL grade
        ev = create_evidence("EV_NO_KL", "PA_TEST", "Imaging", "2026-06-01T10:00:00", "Knee X-ray report", pt_weeks_completed=8)
        outcome, details = evaluate_policy_criteria_against_evidence("AETNA_POL_KNEE_01", [ev])
        self.assertEqual(outcome, "REQUEST_MORE_INFORMATION")
        self.assertIn("Missing required Kellgren-Lawrence (KL) grade documentation", details["failed_criteria"][0])

    def test_cardio_policy_criteria_evaluation(self):
        # Cardio policy missing stress test & angina documentation -> REQUEST_MORE_INFORMATION
        ev_empty = create_evidence("EV_CARDIO_1", "PA_TEST", "Consultation", "2026-06-01T10:00:00", "Cardio consult notes")
        outcome1, details1 = evaluate_policy_criteria_against_evidence("AETNA_POL_CARDIO_03", [ev_empty])
        self.assertEqual(outcome1, "REQUEST_MORE_INFORMATION")

        # Cardio policy with valid abnormal stress test and refractory angina -> APPROVE
        ev_valid = create_evidence("EV_CARDIO_2", "PA_TEST", "Consultation", "2026-06-01T10:00:00", "Abnormal stress test and refractory angina documented", abnormal_stress_test=True, refractory_angina=True)
        outcome2, details2 = evaluate_policy_criteria_against_evidence("AETNA_POL_CARDIO_03", [ev_valid])
        self.assertEqual(outcome2, "APPROVE")

    def test_scenario_7_end_to_end_rag_failure_pipeline(self):
        scenarios = generate_8_scenarios()
        scenario_7 = [s for s in scenarios if s.scenario_id == 7][0]
        self.assertEqual(scenario_7.payer_linkage.policy_lookup_mode, "intentional_rag_failure")
        
        # Executes end-to-end policy retrieval with intentional_rag_failure mode
        outcome, details = evaluate_policy_criteria_against_evidence(
            scenario_7.payer_linkage.policy_id,
            scenario_7.submitted_evidence,
            lookup_mode=scenario_7.payer_linkage.policy_lookup_mode
        )
        self.assertEqual(outcome, "HUMAN_REVIEW")
        self.assertIn("RAG Retrieval Error", details["failed_criteria"][0])

    def test_exact_db_column_schemas(self):
        out_dir = os.path.join(self.tmp_dir, "DATA-VERSION1")
        export_deliverables(out_dir)
        patient_db = os.path.join(out_dir, "big_patient_data.db")
        payer_db = os.path.join(out_dir, "payer_data.db")
        
        patient_cols_checked = validate_db_table_columns(patient_db, EXPECTED_PATIENT_DB_SCHEMAS)
        payer_cols_checked = validate_db_table_columns(payer_db, EXPECTED_PAYER_DB_SCHEMAS)
        self.assertEqual(patient_cols_checked, 91)
        self.assertEqual(payer_cols_checked, 43)

    def test_sqlite_adapter_transformation(self):
        out_dir = os.path.join(self.tmp_dir, "DATA-VERSION1")
        export_deliverables(out_dir)
        patient_db = os.path.join(out_dir, "big_patient_data.db")
        payer_db = os.path.join(out_dir, "payer_data.db")
        
        claim = build_canonical_claim_from_sqlite(patient_db, "CLM_PA001")
        self.assertEqual(claim.claim_id, "CLM_PA001")
        self.assertEqual(claim.patient_id, "PA001")
        self.assertEqual(claim.requested_procedures, ["27447"])
        self.assertEqual(len(claim.submitted_evidence), 2)
        
        context = build_payer_decision_context_from_sqlite(payer_db, "PA001", "AETNA_POL_KNEE_01")
        self.assertEqual(context.member_id, "PA001")
        self.assertEqual(context.payer_id, "Aetna")
        self.assertTrue(context.is_eligible)

    def test_persisted_resubmission_history_in_db(self):
        out_dir = os.path.join(self.tmp_dir, "DATA-VERSION1")
        export_deliverables(out_dir)
        patient_db = os.path.join(out_dir, "big_patient_data.db")
        
        conn = sqlite3.connect(patient_db)
        cursor = conn.cursor()
        cursor.execute("SELECT submission_id, attempt_number, status, submitted_evidence_ids FROM claim_submissions WHERE claim_id = 'CLM_RESUB_PA003' ORDER BY attempt_number ASC")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "SUB_CLM_RESUB_PA003_ATT1")
        self.assertEqual(rows[0][1], 1)
        self.assertEqual(rows[0][2], "REQUEST_MORE_INFORMATION")

        self.assertEqual(rows[1][0], "SUB_CLM_RESUB_PA003_ATT2")
        self.assertEqual(rows[1][1], 2)
        self.assertEqual(rows[1][2], "APPROVE")
        self.assertIn("EV_RESUB_PA003_PT", rows[1][3])

    def test_scenario_1_criteria_approval(self):
        scenarios = generate_8_scenarios()
        scenario_1 = [s for s in scenarios if s.scenario_id == 1][0]
        outcome, details = evaluate_policy_criteria_against_evidence(scenario_1.payer_linkage.policy_id, scenario_1.submitted_evidence)
        self.assertEqual(outcome, "APPROVE")
        self.assertEqual(len(details["failed_criteria"]), 0)

    def test_scenario_2_failed_criterion_rejection(self):
        scenarios = generate_8_scenarios()
        scenario_2 = [s for s in scenarios if s.scenario_id == 2][0]
        outcome, details = evaluate_policy_criteria_against_evidence(scenario_2.payer_linkage.policy_id, scenario_2.submitted_evidence)
        self.assertEqual(outcome, "REJECT")
        self.assertTrue(len(details["failed_criteria"]) > 0)
        failed_item = details["failed_criteria"][0]
        self.assertIn("1 week PT", failed_item["actual_patient_value"])


if __name__ == "__main__":
    unittest.main()
