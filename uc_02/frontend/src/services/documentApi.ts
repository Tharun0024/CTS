// Document upload service — Phase 6: wired to the real FastAPI V1 boundary
// (Phase 5B document ingestion: upload → extract → provider evidence → V1
// pipeline, with provenance). The backend owns extraction and evidence ids.

import { apiFetch } from './api';
import { getClaimDetails } from './claimsApi';
import type { DocumentRef } from '../types/claim';

interface IngestResponse {
  patient_id?: string;
  document_id?: string;
  evidence_id?: string;
  evidence_key?: string;
  filename?: string;
  status?: string;
  [key: string]: unknown;
}

function bytesToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

// POST /api/simulation/documents — the claim's patient_id anchors ingestion.
export async function uploadDocuments(
  claimId: string,
  files: File[]
): Promise<{ claim_id: string; documents: DocumentRef[] }> {
  const details = await getClaimDetails(claimId);
  const patientId = details.patient.patient_id;
  if (!patientId || patientId === 'UNKNOWN') {
    throw new Error(`Claim ${claimId} has no resolvable patient_id for document ingestion.`);
  }

  const uploaded: DocumentRef[] = [];
  for (const file of files) {
    const buffer = await file.arrayBuffer();
    const body = await apiFetch<IngestResponse>('/simulation/documents', {
      method: 'POST',
      body: JSON.stringify({
        patient_id: patientId,
        filename: file.name,
        content_b64: bytesToBase64(buffer),
      }),
    });
    uploaded.push({
      document_id: body.document_id ?? body.evidence_id ?? `DOC-${Date.now()}`,
      file_name: file.name,
      file_type: file.type,
      uploaded_at: new Date().toISOString(),
    });
  }
  return { claim_id: claimId, documents: uploaded };
}
