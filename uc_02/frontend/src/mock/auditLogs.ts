export interface AuditLog {
  log_id: string;
  user: string;
  role: 'Admin' | 'Billing Specialist' | 'Clinical Coordinator' | 'Physician' | 'System';
  action: string;
  action_type: 'CREATE' | 'UPDATE' | 'DELETE' | 'VIEW' | 'LOGIN' | 'LOGOUT' | 'SUBMIT' | 'APPROVE' | 'REJECT' | 'EXPORT';
  resource_type: 'Claim' | 'Patient' | 'Document' | 'Authorization' | 'Payment' | 'User' | 'Report' | 'Settings' | 'System';
  resource_id?: string;
  description: string;
  timestamp: string;
  ip_address: string;
  status: 'Success' | 'Failed' | 'Warning';
}

export const mockAuditLogs: AuditLog[] = [
  { log_id:'LOG-001', user:'Dr. Karen Ellis', role:'Physician', action:'Submitted Claim', action_type:'SUBMIT', resource_type:'Claim', resource_id:'CLM-001', description:'Submitted claim CLM-001 for Total Knee Replacement (PAT-001)', timestamp:'2026-08-11T10:30:12Z', ip_address:'192.168.1.14', status:'Success' },
  { log_id:'LOG-002', user:'System', role:'System', action:'Status Updated', action_type:'UPDATE', resource_type:'Claim', resource_id:'CLM-001', description:'Claim CLM-001 status changed: SUBMITTED → PROCESSING', timestamp:'2026-08-11T10:31:05Z', ip_address:'127.0.0.1', status:'Success' },
  { log_id:'LOG-003', user:'System', role:'System', action:'Claim Accepted', action_type:'APPROVE', resource_type:'Claim', resource_id:'CLM-001', description:'Claim CLM-001 automatically approved — all 4 criteria met', timestamp:'2026-08-11T11:00:22Z', ip_address:'127.0.0.1', status:'Success' },
  { log_id:'LOG-004', user:'billing.admin@hospital.org', role:'Billing Specialist', action:'Viewed Claim', action_type:'VIEW', resource_type:'Claim', resource_id:'CLM-002', description:'Viewed claim CLM-002 details (Sarah Thompson)', timestamp:'2026-08-11T09:35:00Z', ip_address:'192.168.1.22', status:'Success' },
  { log_id:'LOG-005', user:'Dr. Marcus Reid', role:'Physician', action:'Uploaded Document', action_type:'CREATE', resource_type:'Document', resource_id:'DOC-003', description:'Uploaded gp_referral.pdf for claim CLM-002', timestamp:'2026-08-10T13:55:10Z', ip_address:'192.168.1.18', status:'Success' },
  { log_id:'LOG-006', user:'System', role:'System', action:'Claim Rejected', action_type:'REJECT', resource_type:'Claim', resource_id:'CLM-002', description:'Claim CLM-002 rejected: INSUFFICIENT_DOCUMENTATION', timestamp:'2026-08-11T09:30:05Z', ip_address:'127.0.0.1', status:'Success' },
  { log_id:'LOG-007', user:'admin@hospital.org', role:'Admin', action:'User Login', action_type:'LOGIN', resource_type:'System', description:'Admin user logged in from Chicago office', timestamp:'2026-08-12T08:01:44Z', ip_address:'203.0.113.5', status:'Success' },
  { log_id:'LOG-008', user:'billing.admin@hospital.org', role:'Billing Specialist', action:'Exported Report', action_type:'EXPORT', resource_type:'Report', description:'Exported monthly claims summary report (July 2026)', timestamp:'2026-08-12T09:15:22Z', ip_address:'192.168.1.22', status:'Success' },
  { log_id:'LOG-009', user:'Dr. James Hartley', role:'Physician', action:'Submitted Claim', action_type:'SUBMIT', resource_type:'Claim', resource_id:'CLM-004', description:'Submitted claim CLM-004 for Cardiac Catheterization (PAT-004)', timestamp:'2026-08-09T11:00:33Z', ip_address:'192.168.1.31', status:'Success' },
  { log_id:'LOG-010', user:'coord@hospital.org', role:'Clinical Coordinator', action:'Missing Info Uploaded', action_type:'UPDATE', resource_type:'Claim', resource_id:'CLM-003', description:'Uploaded lab results for claim CLM-003 (Robert Chen)', timestamp:'2026-08-11T14:20:05Z', ip_address:'192.168.1.19', status:'Success' },
  { log_id:'LOG-011', user:'unknown@external.com', role:'Admin', action:'Failed Login Attempt', action_type:'LOGIN', resource_type:'System', description:'Failed login attempt — invalid credentials', timestamp:'2026-08-12T07:45:11Z', ip_address:'198.51.100.42', status:'Failed' },
  { log_id:'LOG-012', user:'System', role:'System', action:'Authorization Expired', action_type:'UPDATE', resource_type:'Authorization', resource_id:'AUTH-010', description:'Authorization AUTH-010 expired for Dorothy Singh', timestamp:'2026-08-12T00:00:01Z', ip_address:'127.0.0.1', status:'Warning' },
  { log_id:'LOG-013', user:'admin@hospital.org', role:'Admin', action:'Settings Updated', action_type:'UPDATE', resource_type:'Settings', description:'Hospital notification preferences updated', timestamp:'2026-08-10T11:30:00Z', ip_address:'203.0.113.5', status:'Success' },
  { log_id:'LOG-014', user:'billing.admin@hospital.org', role:'Billing Specialist', action:'Payment Recorded', action_type:'CREATE', resource_type:'Payment', resource_id:'PAY-001', description:'Payment $36,500 recorded for claim CLM-001 (Aetna EFT)', timestamp:'2026-08-12T14:05:33Z', ip_address:'192.168.1.22', status:'Success' },
  { log_id:'LOG-015', user:'coord@hospital.org', role:'Clinical Coordinator', action:'Appointment Scheduled', action_type:'CREATE', resource_type:'Patient', resource_id:'PAT-001', description:'Appointment APT-001 scheduled for John Mitchell with Dr. Karen Ellis', timestamp:'2026-08-11T15:30:00Z', ip_address:'192.168.1.19', status:'Success' },
  { log_id:'LOG-016', user:'Dr. Linda Foster', role:'Physician', action:'Submitted Claim', action_type:'SUBMIT', resource_type:'Claim', resource_id:'CLM-005', description:'Submitted claim CLM-005 for Shoulder Arthroscopy (PAT-005)', timestamp:'2026-08-12T10:00:15Z', ip_address:'192.168.1.15', status:'Success' },
  { log_id:'LOG-017', user:'admin@hospital.org', role:'Admin', action:'User Created', action_type:'CREATE', resource_type:'User', description:'New user account created: dr.newprovider@hospital.org', timestamp:'2026-08-09T09:00:00Z', ip_address:'203.0.113.5', status:'Success' },
  { log_id:'LOG-018', user:'System', role:'System', action:'Resubmission Check', action_type:'UPDATE', resource_type:'Claim', resource_id:'CLM-007', description:'Resubmission analysis initiated for claim CLM-007', timestamp:'2026-08-12T11:00:05Z', ip_address:'127.0.0.1', status:'Success' },
];
