import { mockRequest } from './api';
import type { DocumentRef } from '../types/claim';

// POST /api/claims/{id}/documents
export async function uploadDocuments(
  claimId: string,
  files: File[]
): Promise<{ claim_id: string; documents: DocumentRef[] }> {
  const uploaded: DocumentRef[] = files.map((f, i) => ({
    document_id: `DOC-${Date.now()}-${i}`,
    file_name: f.name,
    file_type: f.type,
    uploaded_at: new Date().toISOString(),
  }));
  return mockRequest({ claim_id: claimId, documents: uploaded }, 800);
}
