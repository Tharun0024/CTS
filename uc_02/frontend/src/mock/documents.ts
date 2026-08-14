export interface HospitalDocument {
  doc_id: string;
  file_name: string;
  file_type: string;
  size_kb: number;
  category: 'Clinical' | 'Administrative' | 'Financial' | 'Lab' | 'Imaging' | 'Legal';
  patient_id?: string;
  patient_name?: string;
  claim_id?: string;
  uploaded_by: string;
  uploaded_at: string;
  status: 'Verified' | 'Pending Review' | 'Rejected';
  tags?: string[];
}

export const mockDocuments: HospitalDocument[] = [
  { doc_id:'DOC-001', file_name:'physician_notes_john_mitchell.pdf', file_type:'PDF', size_kb:245, category:'Clinical', patient_id:'PAT-001', patient_name:'John Mitchell', claim_id:'CLM-001', uploaded_by:'Dr. Karen Ellis', uploaded_at:'2026-08-11T10:28:00Z', status:'Verified', tags:['Orthopedics','Pre-op'] },
  { doc_id:'DOC-002', file_name:'xray_report_john_mitchell.pdf', file_type:'PDF', size_kb:1240, category:'Imaging', patient_id:'PAT-001', patient_name:'John Mitchell', claim_id:'CLM-001', uploaded_by:'Dr. Rachel Bloom', uploaded_at:'2026-08-11T10:28:30Z', status:'Verified', tags:['X-Ray','Knee'] },
  { doc_id:'DOC-003', file_name:'gp_referral_sarah_thompson.pdf', file_type:'PDF', size_kb:128, category:'Clinical', patient_id:'PAT-002', patient_name:'Sarah Thompson', claim_id:'CLM-002', uploaded_by:'Dr. Marcus Reid', uploaded_at:'2026-08-10T13:55:00Z', status:'Verified', tags:['Referral','Spine'] },
  { doc_id:'DOC-004', file_name:'cardiology_report_eleanor_walsh.pdf', file_type:'PDF', size_kb:892, category:'Clinical', patient_id:'PAT-004', patient_name:'Eleanor Walsh', claim_id:'CLM-004', uploaded_by:'Dr. James Hartley', uploaded_at:'2026-08-09T10:58:00Z', status:'Verified', tags:['Cardiology','Catheterization'] },
  { doc_id:'DOC-005', file_name:'stress_test_results.pdf', file_type:'PDF', size_kb:456, category:'Lab', patient_id:'PAT-004', patient_name:'Eleanor Walsh', claim_id:'CLM-004', uploaded_by:'Dr. James Hartley', uploaded_at:'2026-08-09T10:59:00Z', status:'Verified', tags:['Stress Test','Cardiac'] },
  { doc_id:'DOC-006', file_name:'mri_shoulder_david_park.pdf', file_type:'PDF', size_kb:2140, category:'Imaging', patient_id:'PAT-005', patient_name:'David Park', claim_id:'CLM-005', uploaded_by:'Dr. Linda Foster', uploaded_at:'2026-08-12T09:58:00Z', status:'Pending Review', tags:['MRI','Shoulder'] },
  { doc_id:'DOC-007', file_name:'bmi_nutritionist_records.pdf', file_type:'PDF', size_kb:312, category:'Clinical', patient_id:'PAT-006', patient_name:'Linda Reyes', claim_id:'CLM-006', uploaded_by:'Dr. Angela Torres', uploaded_at:'2026-08-11T14:55:00Z', status:'Pending Review', tags:['Bariatric','Nutrition'] },
  { doc_id:'DOC-008', file_name:'mri_lumbar_marcus_johnson.pdf', file_type:'PDF', size_kb:1890, category:'Imaging', patient_id:'PAT-007', patient_name:'Marcus Johnson', claim_id:'CLM-007', uploaded_by:'Dr. Rachel Bloom', uploaded_at:'2026-08-05T08:55:00Z', status:'Verified', tags:['MRI','Lumbar'] },
  { doc_id:'DOC-009', file_name:'orthopedic_evaluation_marcus.pdf', file_type:'PDF', size_kb:220, category:'Clinical', patient_id:'PAT-007', patient_name:'Marcus Johnson', claim_id:'CLM-007', uploaded_by:'Dr. Marcus Reid', uploaded_at:'2026-08-08T10:00:00Z', status:'Verified', tags:['Orthopedic','Spine'] },
  { doc_id:'DOC-010', file_name:'pt_records_patricia_novak.pdf', file_type:'PDF', size_kb:410, category:'Clinical', patient_id:'PAT-008', patient_name:'Patricia Novak', claim_id:'CLM-008', uploaded_by:'Dr. Karen Ellis', uploaded_at:'2026-08-12T11:58:00Z', status:'Verified', tags:['PT','Hip'] },
  { doc_id:'DOC-011', file_name:'hip_xray_patricia_novak.pdf', file_type:'PDF', size_kb:980, category:'Imaging', patient_id:'PAT-008', patient_name:'Patricia Novak', claim_id:'CLM-008', uploaded_by:'Dr. Rachel Bloom', uploaded_at:'2026-08-12T11:59:00Z', status:'Verified', tags:['X-Ray','Hip'] },
  { doc_id:'DOC-012', file_name:'hospital_policy_2026.pdf', file_type:'PDF', size_kb:1024, category:'Administrative', uploaded_by:'Admin', uploaded_at:'2026-01-01T09:00:00Z', status:'Verified', tags:['Policy','Admin'] },
  { doc_id:'DOC-013', file_name:'insurance_contract_aetna.pdf', file_type:'PDF', size_kb:3200, category:'Legal', uploaded_by:'Admin', uploaded_at:'2026-01-15T09:00:00Z', status:'Verified', tags:['Contract','Aetna'] },
  { doc_id:'DOC-014', file_name:'cbc_lab_results_robert_chen.pdf', file_type:'PDF', size_kb:180, category:'Lab', patient_id:'PAT-003', patient_name:'Robert Chen', claim_id:'CLM-003', uploaded_by:'Lab Dept', uploaded_at:'2026-08-11T08:00:00Z', status:'Pending Review', tags:['CBC','Lab'] },
];
