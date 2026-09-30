export interface Payment {
  payment_id: string;
  claim_id: string;
  patient_name: string;
  payer: string;
  procedure: string;
  billed_amount: number;
  approved_amount: number;
  paid_amount: number;
  patient_responsibility: number;
  status: 'Paid' | 'Pending' | 'Partial' | 'Denied' | 'Appealing';
  payment_date?: string;
  due_date: string;
  payment_method?: string;
}

export interface RevenueDataPoint {
  month: string;
  billed: number;
  collected: number;
  denied: number;
}

export interface PayerBreakdown {
  payer: string;
  amount: number;
  count: number;
  color: string;
}
