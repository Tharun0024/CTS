export interface PolicyDoc {
  policy_id: string;
  policy_name: string;
  payer: string;
  policy_type: 'NCD' | 'LCD' | 'Commercial Policy';
  clinical_domain: string;
  effective_date: string;
  last_review_date: string;
  jurisdiction?: string;
  procedure_codes: string[];
  diagnosis_codes: string[];
  coverage_criteria: string[];
  documentation_requirements: string[];
  exclusions: string[];
  source_url?: string;
}

const POLICY_DATABASE: Record<string, PolicyDoc> = {
  'CPB-0660': {
    policy_id: 'CPB-0660',
    policy_name: 'Aetna CPB 0660 – Knee & Hip Arthroplasty',
    payer: 'Aetna',
    policy_type: 'Commercial Policy',
    clinical_domain: 'Orthopedics',
    effective_date: '2025-01-01',
    last_review_date: '2025-11-15',
    procedure_codes: ['27447', '27130'],
    diagnosis_codes: ['M17.11', 'M16.11', 'M79.622', 'M79.652'],
    coverage_criteria: [
      'Evidence of severe joint pain and functional limitation interfering with activities of daily living (ADLs).',
      'Failure of at least 12 weeks of structured conservative non-surgical therapy (e.g., physical therapy, NSAIDs, weight loss, assistive devices).',
      'Radiological confirmation of advanced osteoarthritis (Kellgren-Lawrence Grade III or IV joint space narrowing).',
      'Body Mass Index (BMI) within acceptable limits (<40) to minimize post-operative complications.'
    ],
    documentation_requirements: [
      'Comprehensive physician clinical notes documenting pain severity and impact on ADLs.',
      'Supervised physical therapy reports spanning at least 12 weeks.',
      'Recent radiological report (X-ray or MRI) confirming severe osteoarthritic changes.',
      'Height and weight measurements showing BMI compliance.'
    ],
    exclusions: [
      'Active local or systemic infection at the joint site.',
      'Severe vascular disease of the affected limb.',
      'Neurotrophic arthritis (Charcot joint).',
      'Kellgren-Lawrence Grade I or II (mild changes) unless clinical symptoms are exceptionally severe.'
    ],
    source_url: 'https://www.aetna.com/cpb/medical/data/600_699/0660.html'
  },
  'UHC-SPINE-001': {
    policy_id: 'UHC-SPINE-001',
    policy_name: 'UnitedHealth Spine Surgery Policy (Lumbar Fusion)',
    payer: 'UnitedHealth',
    policy_type: 'Commercial Policy',
    clinical_domain: 'Orthopedics / Spine',
    effective_date: '2025-03-01',
    last_review_date: '2025-12-05',
    procedure_codes: ['22612'],
    diagnosis_codes: ['M51.16', 'M54.5'],
    coverage_criteria: [
      'Severe chronic disabling back pain with or without radiculopathy.',
      'Conservative trial of at least 12 weeks consisting of physical therapy, home exercises, and medical management.',
      'MRI or CT scan documenting disc herniation, stenosis, or spondylolisthesis matching clinical signs.',
      'Evaluation and recommendation by a board-certified orthopedic spine surgeon or neurosurgeon.'
    ],
    documentation_requirements: [
      'Formal evaluation report from an orthopedic spine specialist.',
      'Complete MRI or CT imaging reports showing nerve root compression or spinal instability.',
      'Structured logs of physical therapy and conservative interventions.'
    ],
    exclusions: [
      'Uncontrolled metabolic bone disease (e.g., osteoporosis with high fracture risk).',
      'Active local infection or major psychiatric comorbidities affecting recovery compliance.',
      'Absence of matching radiological abnormalities.'
    ]
  },
  'CGN-IMG-002': {
    policy_id: 'CGN-IMG-002',
    policy_name: 'Cigna Imaging Authorization Policy (CT Abdomen & Pelvis)',
    payer: 'Cigna',
    policy_type: 'Commercial Policy',
    clinical_domain: 'Radiology / Imaging',
    effective_date: '2025-02-15',
    last_review_date: '2025-10-10',
    procedure_codes: ['74178'],
    diagnosis_codes: ['R10.9', 'K92.1'],
    coverage_criteria: [
      'Severe, unexplained abdominal pain associated with systemic signs (fever, weight loss, abnormal blood count).',
      'Suspicion of inflammatory bowel disease, appendicitis, diverticulitis, or intra-abdominal abscess.',
      'Prior conservative evaluation, including physical examination, clinical lab work, and basic imaging (ultrasound/plain X-ray) did not yield a diagnosis.'
    ],
    documentation_requirements: [
      'Recent physician clinical notes with physical examination findings.',
      'Lab work reports (complete blood count, metabolic panel) within the last 90 days.',
      'Prior ultrasound or abdominal X-ray imaging reports.'
    ],
    exclusions: [
      'Routine surveillance imaging without clinical change or symptoms.',
      'Screening for conditions where low-dose or non-radiating imaging (e.g., MRI, ultrasound) is clinically equivalent.'
    ]
  },
  'BCBS-CARD-001': {
    policy_id: 'BCBS-CARD-001',
    policy_name: 'BCBS Cardiac Procedures Policy (Cardiac Catheterization)',
    payer: 'BlueCross BlueShield',
    policy_type: 'Commercial Policy',
    clinical_domain: 'Cardiology',
    effective_date: '2025-05-01',
    last_review_date: '2025-08-20',
    procedure_codes: ['93460'],
    diagnosis_codes: ['I25.10', 'I20.9'],
    coverage_criteria: [
      'Documented stable or unstable angina symptoms (NYHA Class II, III, or IV).',
      'Abnormal non-invasive testing including stress electrocardiography, myocardial perfusion imaging (MPI), or stress echocardiogram.',
      'Documented trial of optimal medical therapy (OMT) including anti-anginal drugs, statins, and antiplatelets for at least 6 months.'
    ],
    documentation_requirements: [
      'Cardiologist consultation and diagnostic notes.',
      'Stress test reports and electrocardiogram tracings.',
      'Prescription records demonstrating drug compliance.'
    ],
    exclusions: [
      'Asymptomatic patients without evidence of ischemia on non-invasive tests.',
      'Severe comorbidity risk assessment where benefits do not outweigh interventional hazards.'
    ]
  },
  'NCD-20.8.3': {
    policy_id: 'NCD-20.8.3',
    policy_name: 'NCD 20.8.3 – Permanent Cardiac Pacemakers (Single/Dual Chamber)',
    payer: 'CMS',
    policy_type: 'NCD',
    clinical_domain: 'Cardiology',
    effective_date: '2024-08-13',
    last_review_date: '2025-06-12',
    procedure_codes: ['33206', '33207', '33208'],
    diagnosis_codes: ['I49.5', 'I44.2'],
    coverage_criteria: [
      'Documented symptomatic bradycardia due to sinus node dysfunction (Sick Sinus Syndrome).',
      'Second-degree or third-degree heart block (AV block) with documented clinical signs.',
      'Symptoms must be directly correlated with bradycardic events (syncope, dizziness, confusion).'
    ],
    documentation_requirements: [
      'EKG or Holter monitor tracing documenting heart block or sinus bradycardia.',
      'Clinical logs showing correlation of symptoms with documented low heart rates.'
    ],
    exclusions: [
      'Reversible causes of bradycardia (e.g., drug toxicity, electrolyte imbalance, hypothermia).',
      'Prophylactic insertion in asymptomatic heart block without clinical indicators.'
    ]
  },
  'LCD-L36575': {
    policy_id: 'LCD-L36575',
    policy_name: 'LCD L36575 – Total Knee Arthroplasty',
    payer: 'CMS',
    policy_type: 'LCD',
    clinical_domain: 'Orthopedics',
    effective_date: '2024-10-01',
    last_review_date: '2025-07-15',
    jurisdiction: 'MAC Jurisdiction J-K',
    procedure_codes: ['27447'],
    diagnosis_codes: ['M17.0', 'M17.11'],
    coverage_criteria: [
      'Advanced osteoarthritis of the knee joint with Kellgren-Lawrence Grade III or IV joint space narrowing on imaging.',
      'Failure of conservative treatment (including home therapy, physical therapy, intra-articular steroid or hyaluronic acid injections) for at least 3 months.',
      'Severe disabling pain restricting walking and basic daily living activities.'
    ],
    documentation_requirements: [
      'Detailed clinical notes documenting pain score, walking distance limit, and ADL limitations.',
      'Radiology report from a certified radiologist within 6 months.',
      'Documentation of dates and responses to non-surgical treatment.'
    ],
    exclusions: [
      'Active infection of the knee joint.',
      'Inability to comply with post-operative rehabilitation due to neurological or mental conditions.'
    ]
  }
};

export function viewPolicyDocument(policyId: string, customPolicyName?: string, customPayer?: string) {
  const normalizedId = Object.keys(POLICY_DATABASE).find(
    k => k.toLowerCase() === policyId.toLowerCase()
  );

  const policy: PolicyDoc = normalizedId ? POLICY_DATABASE[normalizedId] : {
    policy_id: policyId || 'UNKNOWN-ID',
    policy_name: customPolicyName || 'Default Insurance Coverage Guideline',
    payer: customPayer || 'Insurance Provider',
    policy_type: (policyId.toLowerCase().startsWith('ncd') ? 'NCD' : policyId.toLowerCase().startsWith('lcd') ? 'LCD' : 'Commercial Policy') as any,
    clinical_domain: 'General Medical',
    effective_date: '2025-01-01',
    last_review_date: '2025-10-01',
    procedure_codes: ['N/A'],
    diagnosis_codes: ['N/A'],
    coverage_criteria: [
      'The procedure must be medically necessary for the diagnosis and treatment of the patient\'s condition.',
      'Documentation must substantiate that conservative medical management has been tried and failed.',
      'Evidence must match standard ICD-10 and CPT coding specifications.'
    ],
    documentation_requirements: [
      'Clinical consultation notes describing the history and physical examination.',
      'Supporting diagnostic tests (imaging, laboratory findings, or functional assessments).'
    ],
    exclusions: [
      'Experimental, investigational, or unproven treatments.',
      'Procedures performed solely for cosmetic or convenience purposes.'
    ]
  };

  const policyWindow = window.open('', '_blank', 'noopener,noreferrer');
  if (!policyWindow) {
    alert('Please allow popups to view policy details.');
    return;
  }

  const mapList = (arr: string[]) => arr.map(item => `<li style="margin-bottom: 8px; line-height: 1.5;">${item}</li>`).join('');
  const mapBadge = (val: string) => `<span style="display: inline-block; padding: 4px 8px; background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; font-family: monospace; font-size: 12px; margin-right: 4px;">${val}</span>`;

  policyWindow.document.write(`
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>${policy.policy_id} - Policy Companion</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f8fafc;
            color: #334155;
            margin: 0;
            padding: 0;
          }
          header {
            background-color: #0f172a;
            color: #ffffff;
            padding: 24px 40px;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
          }
          .container {
            max-width: 900px;
            margin: 40px auto;
            background: #ffffff;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgb(0 0 0 / 0.05);
            border: 1px solid #e2e8f0;
          }
          h1 {
            margin: 0 0 8px 0;
            font-size: 24px;
            font-weight: 800;
          }
          h2 {
            font-size: 16px;
            font-weight: 700;
            color: #0284c7;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 32px;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 8px;
            margin-bottom: 16px;
          }
          .meta-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-top: 16px;
            background-color: #f8fafc;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
          }
          .meta-item strong {
            display: block;
            font-size: 11px;
            text-transform: uppercase;
            color: #64748b;
            margin-bottom: 4px;
          }
          .meta-item span {
            font-size: 14px;
            font-weight: 600;
            color: #1e293b;
          }
          ul, ol {
            padding-left: 20px;
            margin: 0;
          }
          .footer {
            margin-top: 48px;
            text-align: center;
            font-size: 12px;
            color: #94a3b8;
            border-top: 1px solid #e2e8f0;
            padding-top: 16px;
          }
          .btn-close {
            display: inline-block;
            margin-top: 24px;
            padding: 10px 20px;
            background-color: #0f172a;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            border: none;
          }
          .btn-close:hover {
            background-color: #1e293b;
          }
        </style>
      </head>
      <body>
        <header>
          <div style="max-width: 900px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <span style="font-size: 11px; font-weight: 800; background-color: #0284c7; color: white; padding: 4px 8px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.05em; display: inline-block; margin-bottom: 6px;">${policy.policy_type}</span>
              <h1>${policy.policy_name}</h1>
              <div style="font-size: 13px; color: #94a3b8; font-weight: 500;">
                Clinical Domain: ${policy.clinical_domain} | ID: ${policy.policy_id}
              </div>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 16px; font-weight: 800; color: #0284c7;">${policy.payer.toUpperCase()}</div>
              <div style="font-size: 11px; color: #64748b; font-weight: bold; margin-top: 2px;">SECURE COVERAGE</div>
            </div>
          </div>
        </header>

        <div class="container">
          <div class="meta-grid">
            <div class="meta-item">
              <strong>Payer Name</strong>
              <span>${policy.payer}</span>
            </div>
            <div class="meta-item">
              <strong>Policy Type</strong>
              <span>${policy.policy_type}</span>
            </div>
            <div class="meta-item">
              <strong>Effective Date</strong>
              <span>${policy.effective_date}</span>
            </div>
            <div class="meta-item">
              <strong>Last Reviewed Date</strong>
              <span>${policy.last_review_date}</span>
            </div>
            ${policy.jurisdiction ? `
            <div class="meta-item" style="grid-column: span 2;">
              <strong>MAC Jurisdiction / Contractor Context</strong>
              <span>${policy.jurisdiction}</span>
            </div>` : ''}
          </div>

          <h2>1. Coding and Identifiers</h2>
          <div style="margin-bottom: 12px;">
            <strong style="font-size: 13px; color: #64748b; display: block; margin-bottom: 6px;">Applicable CPT/HCPCS Procedure Codes:</strong>
            <div>${policy.procedure_codes.map(mapBadge).join('')}</div>
          </div>
          <div style="margin-top: 16px;">
            <strong style="font-size: 13px; color: #64748b; display: block; margin-bottom: 6px;">Associated ICD-10-CM Diagnosis Codes:</strong>
            <div>${policy.diagnosis_codes.map(mapBadge).join('')}</div>
          </div>

          <h2>2. Medical Necessity &amp; Coverage Criteria</h2>
          <ul>
            ${mapList(policy.coverage_criteria)}
          </ul>

          <h2>3. Clinical Documentation Requirements</h2>
          <ul>
            ${mapList(policy.documentation_requirements)}
          </ul>

          <h2>4. Exclusions and Limitations</h2>
          <ul style="color: #991b1b;">
            ${mapList(policy.exclusions)}
          </ul>

          ${policy.source_url ? `
          <h2>5. External References</h2>
          <p style="font-size: 13px;">
            For official policy text and supplementary guidelines, visit: 
            <a href="${policy.source_url}" target="_blank" style="color: #0284c7; font-weight: 600; word-break: break-all;">${policy.source_url}</a>
          </p>` : ''}

          <div style="text-align: center; margin-top: 30px;">
            <button class="btn-close" onclick="window.close()">Close Document Viewer</button>
          </div>

          <div class="footer">
            AuthFlow V1 Policy Companion Portal &copy; 2026. Confidential for clinical review only.
          </div>
        </div>
      </body>
    </html>
  `);
  policyWindow.document.close();
}
