import { mockRequest } from './api';
import { mockPayments, mockRevenueData, mockPayerBreakdown } from '../mock/payments';
import type { Payment, RevenueDataPoint, PayerBreakdown } from '../types/payment';

let store: Payment[] = [...mockPayments];

export async function getPayments(): Promise<Payment[]> {
  return mockRequest([...store]);
}

export async function getRevenueData(): Promise<RevenueDataPoint[]> {
  return mockRequest([...mockRevenueData]);
}

export async function getPayerBreakdown(): Promise<PayerBreakdown[]> {
  return mockRequest([...mockPayerBreakdown]);
}

export async function recordPayment(id: string, amount: number, method: string): Promise<Payment> {
  const idx = store.findIndex(p => p.payment_id === id);
  if (idx !== -1) {
    store[idx] = {
      ...store[idx],
      paid_amount: store[idx].paid_amount + amount,
      payment_method: method,
      payment_date: new Date().toISOString().split('T')[0],
      status: store[idx].approved_amount <= store[idx].paid_amount + amount ? 'Paid' : 'Partial',
    };
  }
  return mockRequest({ ...store[idx] }, 400);
}
