import { mockRequest } from './api';
import { mockAuditLogs } from '../mock/auditLogs';
import type { AuditLog } from '../mock/auditLogs';

export type { AuditLog };

export async function getAuditLogs(): Promise<AuditLog[]> {
  return mockRequest([...mockAuditLogs]);
}
