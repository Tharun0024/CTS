import type { Payment, RevenueDataPoint, PayerBreakdown } from '../types/payment';

export const mockPayments: Payment[] = [
  {
    payment_id: 'PAY-001', claim_id: 'CLM-001', patient_name: 'John Mitchell',
    payer: 'Aetna', procedure: 'Total Knee Replacement',
    billed_amount: 42000, approved_amount: 36500, paid_amount: 36500, patient_responsibility: 2100,
    status: 'Paid', payment_date: '2026-08-12', due_date: '2026-08-30', payment_method: 'EFT',
  },
  {
    payment_id: 'PAY-002', claim_id: 'CLM-002', patient_name: 'Sarah Thompson',
    payer: 'UnitedHealth', procedure: 'Lumbar Spinal Fusion',
    billed_amount: 58000, approved_amount: 0, paid_amount: 0, patient_responsibility: 0,
    status: 'Denied', due_date: '2026-09-01',
  },
  {
    payment_id: 'PAY-003', claim_id: 'CLM-004', patient_name: 'Eleanor Walsh',
    payer: 'BlueCross BlueShield', procedure: 'Cardiac Catheterization',
    billed_amount: 28000, approved_amount: 22000, paid_amount: 11000, patient_responsibility: 3500,
    status: 'Partial', due_date: '2026-09-05',
  },
  {
    payment_id: 'PAY-004', claim_id: 'CLM-005', patient_name: 'David Park',
    payer: 'Humana', procedure: 'Shoulder Arthroscopy',
    billed_amount: 18500, approved_amount: 15200, paid_amount: 0, patient_responsibility: 1200,
    status: 'Pending', due_date: '2026-09-10',
  },
  {
    payment_id: 'PAY-005', claim_id: 'CLM-008', patient_name: 'Patricia Novak',
    payer: 'Aetna', procedure: 'Hip Replacement',
    billed_amount: 47000, approved_amount: 38000, paid_amount: 0, patient_responsibility: 2500,
    status: 'Pending', due_date: '2026-09-15',
  },
  {
    payment_id: 'PAY-006', claim_id: 'CLM-006', patient_name: 'Linda Reyes',
    payer: 'Anthem', procedure: 'Bariatric Surgery',
    billed_amount: 32000, approved_amount: 28500, paid_amount: 28500, patient_responsibility: 1800,
    status: 'Paid', payment_date: '2026-08-10', due_date: '2026-08-25', payment_method: 'Check',
  },
  {
    payment_id: 'PAY-007', claim_id: 'CLM-007', patient_name: 'Marcus Johnson',
    payer: 'UnitedHealth', procedure: 'Lumbar Spinal Fusion',
    billed_amount: 55000, approved_amount: 46000, paid_amount: 0, patient_responsibility: 3000,
    status: 'Appealing', due_date: '2026-09-20',
  },
  {
    payment_id: 'PAY-008', claim_id: 'CLM-003', patient_name: 'Robert Chen',
    payer: 'Cigna', procedure: 'CT Scan – Abdomen & Pelvis',
    billed_amount: 4800, approved_amount: 3600, paid_amount: 3600, patient_responsibility: 300,
    status: 'Paid', payment_date: '2026-08-11', due_date: '2026-08-20', payment_method: 'EFT',
  },
];

export const mockRevenueData: RevenueDataPoint[] = [
  { month: 'Mar', billed: 210000, collected: 168000, denied: 24000 },
  { month: 'Apr', billed: 245000, collected: 192000, denied: 31000 },
  { month: 'May', billed: 230000, collected: 181000, denied: 28000 },
  { month: 'Jun', billed: 275000, collected: 218000, denied: 33000 },
  { month: 'Jul', billed: 292000, collected: 234000, denied: 29000 },
  { month: 'Aug', billed: 285000, collected: 198000, denied: 42000 },
];

export const mockPayerBreakdown: PayerBreakdown[] = [
  { payer: 'Aetna',             amount: 75000, count: 24, color: '#10b981' },
  { payer: 'UnitedHealth',      amount: 62000, count: 18, color: '#3b82f6' },
  { payer: 'BlueCross',         amount: 48000, count: 14, color: '#8b5cf6' },
  { payer: 'Cigna',             amount: 37000, count: 11, color: '#f59e0b' },
  { payer: 'Humana',            amount: 29000, count:  9, color: '#ec4899' },
  { payer: 'Anthem',            amount: 21000, count:  6, color: '#06b6d4' },
];
