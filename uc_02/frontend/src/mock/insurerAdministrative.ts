import type { InsurerAdministrativeData } from '../types/insurerAdministrative';

export const mockInsurerAdministrativeData: InsurerAdministrativeData[] = [
  {
    patient_id: 'PAT-001',
    patient_name: 'John Mitchell',
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2024-01-01',
      copay_amount: 30,
      deductible_met: 1250,
      deductible_total: 2000,
    },
    prior_auth_history: [
      {
        auth_id: 'AUTH-001',
        procedure: 'Total Knee Replacement',
        procedure_code: '27447',
        requested_date: '2026-08-11',
        decision_date: '2026-08-11',
        status: 'Approved',
        notes: 'All policy criteria satisfied.',
      },
      {
        auth_id: 'AUTH-088',
        procedure: 'Knee MRI Scan',
        procedure_code: '73721',
        requested_date: '2026-05-10',
        decision_date: '2026-05-12',
        status: 'Approved',
        notes: 'Medical necessity criteria met.',
      }
    ],
    claim_history: [
      {
        claim_id: 'CLM-001',
        procedure: 'Total Knee Replacement',
        procedure_code: '27447',
        service_date: '2026-08-20',
        amount_billed: 35000,
        amount_paid: 28000,
        status: 'Accepted',
      },
      {
        claim_id: 'CLM-109',
        procedure: 'Pre-operative Lab Profile',
        procedure_code: '80053',
        service_date: '2026-08-05',
        amount_billed: 450,
        amount_paid: 380,
        status: 'Accepted',
      }
    ],
    utilization_frequency: {
      visits_this_year: 14,
      max_allowed_visits_per_year: 30,
      procedures_performed: 2,
      er_visits: 0,
      pt_sessions_count: 12,
      pt_sessions_allowed: 20,
    },
    coverage_details: {
      plan_type: 'PPO',
      group_number: 'AET-GRP-9012',
      subscriber_id: 'SUB-AET-5541',
      benefit_details: {
        in_network_coverage_percent: 80,
        out_of_network_coverage_percent: 60,
        max_out_of_pocket: 5000,
        max_out_of_pocket_met: 1850,
      }
    }
  },
  {
    patient_id: 'PAT-002',
    patient_name: 'Sarah Thompson',
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2024-03-15',
      copay_amount: 40,
      deductible_met: 1800,
      deductible_total: 2500,
    },
    prior_auth_history: [
      {
        auth_id: 'AUTH-002',
        procedure: 'Lumbar Spinal Fusion',
        procedure_code: '22612',
        requested_date: '2026-08-10',
        decision_date: '2026-08-11',
        status: 'Denied',
        notes: 'Missing MRI and orthopedic evaluation.',
      }
    ],
    claim_history: [
      {
        claim_id: 'CLM-002',
        procedure: 'Lumbar Spinal Fusion',
        procedure_code: '22612',
        service_date: '2026-08-22',
        amount_billed: 58000,
        amount_paid: 0,
        status: 'Rejected',
      },
      {
        claim_id: 'CLM-202',
        procedure: 'Physical Therapy Session',
        procedure_code: '97110',
        service_date: '2026-07-10',
        amount_billed: 250,
        amount_paid: 200,
        status: 'Accepted',
      }
    ],
    utilization_frequency: {
      visits_this_year: 8,
      max_allowed_visits_per_year: 25,
      procedures_performed: 1,
      er_visits: 1,
      pt_sessions_count: 6,
      pt_sessions_allowed: 15,
    },
    coverage_details: {
      plan_type: 'HMO',
      group_number: 'UHC-GRP-7721',
      subscriber_id: 'SUB-UHC-8812',
      benefit_details: {
        in_network_coverage_percent: 90,
        out_of_network_coverage_percent: 0,
        max_out_of_pocket: 4000,
        max_out_of_pocket_met: 2200,
      }
    }
  },
  {
    patient_id: 'PAT-003',
    patient_name: 'Robert Chen',
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2023-06-01',
      copay_amount: 25,
      deductible_met: 500,
      deductible_total: 1500,
    },
    prior_auth_history: [
      {
        auth_id: 'AUTH-003',
        procedure: 'CT Scan – Abdomen & Pelvis',
        procedure_code: '74178',
        requested_date: '2026-08-11',
        decision_date: '2026-08-11',
        status: 'Pending',
        notes: 'Awaiting lab results upload.',
      }
    ],
    claim_history: [
      {
        claim_id: 'CLM-003',
        procedure: 'CT Scan – Abdomen & Pelvis',
        procedure_code: '74178',
        service_date: '2026-08-18',
        amount_billed: 2200,
        status: 'In Progress',
      }
    ],
    utilization_frequency: {
      visits_this_year: 11,
      max_allowed_visits_per_year: 40,
      procedures_performed: 3,
      er_visits: 2,
      pt_sessions_count: 0,
      pt_sessions_allowed: 10,
    },
    coverage_details: {
      plan_type: 'PPO',
      group_number: 'CGN-GRP-4411',
      subscriber_id: 'SUB-CGN-3301',
      benefit_details: {
        in_network_coverage_percent: 85,
        out_of_network_coverage_percent: 70,
        max_out_of_pocket: 6000,
        max_out_of_pocket_met: 1200,
      }
    }
  },
  {
    patient_id: 'PAT-004',
    patient_name: 'Eleanor Walsh',
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2021-09-01',
      copay_amount: 15,
      deductible_met: 2000,
      deductible_total: 2000,
    },
    prior_auth_history: [
      {
        auth_id: 'AUTH-004',
        procedure: 'Cardiac Catheterization',
        procedure_code: '93460',
        requested_date: '2026-08-09',
        decision_date: '2026-08-10',
        status: 'Pending',
        notes: 'Escalated for human clinical review.',
      }
    ],
    claim_history: [
      {
        claim_id: 'CLM-004',
        procedure: 'Cardiac Catheterization',
        procedure_code: '93460',
        service_date: '2026-08-25',
        amount_billed: 18500,
        status: 'In Progress',
      }
    ],
    utilization_frequency: {
      visits_this_year: 24,
      max_allowed_visits_per_year: 50,
      procedures_performed: 6,
      er_visits: 3,
      pt_sessions_count: 4,
      pt_sessions_allowed: 30,
    },
    coverage_details: {
      plan_type: 'PPO',
      group_number: 'BCBS-GRP-1100',
      subscriber_id: 'SUB-BCBS-9090',
      benefit_details: {
        in_network_coverage_percent: 90,
        out_of_network_coverage_percent: 75,
        max_out_of_pocket: 3000,
        max_out_of_pocket_met: 3000,
      }
    }
  },
  {
    patient_id: 'PAT-005',
    patient_name: 'David Park',
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2025-02-01',
      copay_amount: 35,
      deductible_met: 400,
      deductible_total: 1500,
    },
    prior_auth_history: [
      {
        auth_id: 'AUTH-005',
        procedure: 'Shoulder Arthroscopy',
        procedure_code: '29807',
        requested_date: '2026-08-12',
        status: 'Pending',
      }
    ],
    claim_history: [
      {
        claim_id: 'CLM-005',
        procedure: 'Shoulder Arthroscopy',
        procedure_code: '29807',
        service_date: '2026-08-30',
        amount_billed: 12000,
        status: 'In Progress',
      }
    ],
    utilization_frequency: {
      visits_this_year: 5,
      max_allowed_visits_per_year: 20,
      procedures_performed: 0,
      er_visits: 0,
      pt_sessions_count: 0,
      pt_sessions_allowed: 12,
    },
    coverage_details: {
      plan_type: 'PPO',
      group_number: 'HUM-GRP-5544',
      subscriber_id: 'SUB-HUM-1122',
      benefit_details: {
        in_network_coverage_percent: 80,
        out_of_network_coverage_percent: 60,
        max_out_of_pocket: 4500,
        max_out_of_pocket_met: 850,
      }
    }
  },
  {
    patient_id: 'PAT-006',
    patient_name: 'Linda Reyes',
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2023-11-01',
      copay_amount: 25,
      deductible_met: 1500,
      deductible_total: 1500,
    },
    prior_auth_history: [
      {
        auth_id: 'AUTH-006',
        procedure: 'Bariatric Surgery (Gastric Bypass)',
        procedure_code: '43644',
        requested_date: '2026-08-11',
        decision_date: '2026-08-12',
        status: 'Pending',
        notes: 'Resubmitted with multidisciplinary program history.',
      }
    ],
    claim_history: [
      {
        claim_id: 'CLM-006',
        procedure: 'Bariatric Surgery (Gastric Bypass)',
        procedure_code: '43644',
        service_date: '2026-09-05',
        amount_billed: 42000,
        status: 'In Progress',
      }
    ],
    utilization_frequency: {
      visits_this_year: 9,
      max_allowed_visits_per_year: 30,
      procedures_performed: 1,
      er_visits: 0,
      pt_sessions_count: 0,
      pt_sessions_allowed: 10,
    },
    coverage_details: {
      plan_type: 'PPO',
      group_number: 'ANT-GRP-6622',
      subscriber_id: 'SUB-ANT-4455',
      benefit_details: {
        in_network_coverage_percent: 85,
        out_of_network_coverage_percent: 70,
        max_out_of_pocket: 5000,
        max_out_of_pocket_met: 2200,
      }
    }
  },
  {
    patient_id: 'PAT-007',
    patient_name: 'Marcus Johnson',
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2024-05-20',
      copay_amount: 40,
      deductible_met: 2500,
      deductible_total: 2500,
    },
    prior_auth_history: [
      {
        auth_id: 'AUTH-007',
        procedure: 'Lumbar Spinal Fusion',
        procedure_code: '22612',
        requested_date: '2026-08-05',
        decision_date: '2026-08-12',
        status: 'Pending',
        notes: 'Resubmission under re-evaluation.',
      }
    ],
    claim_history: [
      {
        claim_id: 'CLM-007',
        procedure: 'Lumbar Spinal Fusion',
        procedure_code: '22612',
        service_date: '2026-09-10',
        amount_billed: 62000,
        status: 'In Progress',
      }
    ],
    utilization_frequency: {
      visits_this_year: 15,
      max_allowed_visits_per_year: 25,
      procedures_performed: 2,
      er_visits: 1,
      pt_sessions_count: 10,
      pt_sessions_allowed: 15,
    },
    coverage_details: {
      plan_type: 'HMO',
      group_number: 'UHC-GRP-7721',
      subscriber_id: 'SUB-UHC-0099',
      benefit_details: {
        in_network_coverage_percent: 90,
        out_of_network_coverage_percent: 0,
        max_out_of_pocket: 3500,
        max_out_of_pocket_met: 3500,
      }
    }
  },
  {
    patient_id: 'PAT-008',
    patient_name: 'Patricia Novak',
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2025-01-01',
      copay_amount: 30,
      deductible_met: 1000,
      deductible_total: 2000,
    },
    prior_auth_history: [
      {
        auth_id: 'AUTH-008',
        procedure: 'Hip Replacement',
        procedure_code: '27130',
        requested_date: '2026-08-12',
        status: 'Pending',
      }
    ],
    claim_history: [
      {
        claim_id: 'CLM-008',
        procedure: 'Hip Replacement',
        procedure_code: '27130',
        service_date: '2026-09-15',
        amount_billed: 38000,
        status: 'In Progress',
      }
    ],
    utilization_frequency: {
      visits_this_year: 6,
      max_allowed_visits_per_year: 30,
      procedures_performed: 0,
      er_visits: 0,
      pt_sessions_count: 2,
      pt_sessions_allowed: 20,
    },
    coverage_details: {
      plan_type: 'PPO',
      group_number: 'AET-GRP-9012',
      subscriber_id: 'SUB-AET-2342',
      benefit_details: {
        in_network_coverage_percent: 80,
        out_of_network_coverage_percent: 60,
        max_out_of_pocket: 5000,
        max_out_of_pocket_met: 1500,
      }
    }
  },
  {
    patient_id: 'PAT-009',
    patient_name: "James O'Brien",
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2025-05-01',
      copay_amount: 30,
      deductible_met: 200,
      deductible_total: 1500,
    },
    prior_auth_history: [],
    claim_history: [
      {
        claim_id: 'CLM-009',
        procedure: 'Knee Meniscus Tear Repair',
        procedure_code: '29881',
        service_date: '2026-08-12',
        amount_billed: 8500,
        amount_paid: 6800,
        status: 'Accepted',
      }
    ],
    utilization_frequency: {
      visits_this_year: 3,
      max_allowed_visits_per_year: 20,
      procedures_performed: 1,
      er_visits: 0,
      pt_sessions_count: 0,
      pt_sessions_allowed: 10,
    },
    coverage_details: {
      plan_type: 'PPO',
      group_number: 'CGN-GRP-4411',
      subscriber_id: 'SUB-CGN-8877',
      benefit_details: {
        in_network_coverage_percent: 80,
        out_of_network_coverage_percent: 60,
        max_out_of_pocket: 5500,
        max_out_of_pocket_met: 500,
      }
    }
  },
  {
    patient_id: 'PAT-010',
    patient_name: 'Angela Kim',
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2024-08-01',
      copay_amount: 25,
      deductible_met: 1500,
      deductible_total: 1500,
    },
    prior_auth_history: [
      {
        auth_id: 'AUTH-009',
        procedure: 'Echocardiogram',
        procedure_code: '93306',
        requested_date: '2026-08-01',
        decision_date: '2026-08-10',
        status: 'Approved',
        notes: 'Approved under cardiorespiratory policy checks.',
      }
    ],
    claim_history: [
      {
        claim_id: 'CLM-210',
        procedure: 'Echocardiogram',
        procedure_code: '93306',
        service_date: '2026-08-11',
        amount_billed: 1500,
        amount_paid: 1350,
        status: 'Accepted',
      }
    ],
    utilization_frequency: {
      visits_this_year: 12,
      max_allowed_visits_per_year: 30,
      procedures_performed: 2,
      er_visits: 1,
      pt_sessions_count: 0,
      pt_sessions_allowed: 15,
    },
    coverage_details: {
      plan_type: 'HMO',
      group_number: 'HUM-GRP-5544',
      subscriber_id: 'SUB-HUM-6655',
      benefit_details: {
        in_network_coverage_percent: 90,
        out_of_network_coverage_percent: 0,
        max_out_of_pocket: 3000,
        max_out_of_pocket_met: 1800,
      }
    }
  },
  {
    patient_id: 'PAT-011',
    patient_name: 'Carlos Mendes',
    eligibility: {
      eligible: true,
      coverage_status: 'Inactive',
      effective_date: '2023-01-01',
      termination_date: '2026-07-01',
      copay_amount: 30,
      deductible_met: 0,
      deductible_total: 2000,
    },
    prior_auth_history: [],
    claim_history: [
      {
        claim_id: 'CLM-211',
        procedure: 'Routine Eye Exam',
        procedure_code: '92002',
        service_date: '2026-06-15',
        amount_billed: 180,
        amount_paid: 150,
        status: 'Accepted',
      }
    ],
    utilization_frequency: {
      visits_this_year: 4,
      max_allowed_visits_per_year: 20,
      procedures_performed: 0,
      er_visits: 0,
      pt_sessions_count: 0,
      pt_sessions_allowed: 10,
    },
    coverage_details: {
      plan_type: 'PPO',
      group_number: 'BCBS-GRP-1100',
      subscriber_id: 'SUB-BCBS-1234',
      benefit_details: {
        in_network_coverage_percent: 80,
        out_of_network_coverage_percent: 60,
        max_out_of_pocket: 5000,
        max_out_of_pocket_met: 0,
      }
    }
  },
  {
    patient_id: 'PAT-012',
    patient_name: 'Dorothy Singh',
    eligibility: {
      eligible: true,
      coverage_status: 'Active',
      effective_date: '2022-04-10',
      copay_amount: 15,
      deductible_met: 1500,
      deductible_total: 1500,
    },
    prior_auth_history: [
      {
        auth_id: 'AUTH-010',
        procedure: 'Pulmonary Function Test',
        procedure_code: '94010',
        requested_date: '2026-07-28',
        decision_date: '2026-08-04',
        status: 'Denied',
        notes: 'Expired before use.',
      }
    ],
    claim_history: [
      {
        claim_id: 'CLM-212',
        procedure: 'Pulmonary Function Test',
        procedure_code: '94010',
        service_date: '2026-08-05',
        amount_billed: 950,
        amount_paid: 0,
        status: 'Rejected',
      }
    ],
    utilization_frequency: {
      visits_this_year: 21,
      max_allowed_visits_per_year: 45,
      procedures_performed: 4,
      er_visits: 3,
      pt_sessions_count: 10,
      pt_sessions_allowed: 20,
    },
    coverage_details: {
      plan_type: 'PPO',
      group_number: 'ANT-GRP-6622',
      subscriber_id: 'SUB-ANT-9911',
      benefit_details: {
        in_network_coverage_percent: 90,
        out_of_network_coverage_percent: 70,
        max_out_of_pocket: 2000,
        max_out_of_pocket_met: 2000,
      }
    }
  }
];
