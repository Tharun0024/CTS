import { mockRequest } from './api';
import { mockResubmissions } from '../mock/resubmission';
import type { ResubmissionAnalysis } from '../types/resubmission';

// GET /api/claims/{id}/resubmission
export async function getResubmissionAnalysis(claimId: string): Promise<ResubmissionAnalysis> {
  const data = mockResubmissions[claimId] ?? mockResubmissions['CLM-002'];
  return mockRequest(data);
}
