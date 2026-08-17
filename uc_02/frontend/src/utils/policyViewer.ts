// Policy context viewer — renders ONLY data that actually exists on the live
// backend claim record (policy identity, evaluated criteria, submitted
// evidence, outstanding information requests). V1 has no policy-document
// endpoint, so nothing here invents policy text, dates, or criteria; sections
// without recorded data show an honest empty state instead.

import type { ClaimDetails } from '../types/claim';

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function badge(value: string): string {
  return `<span style="display: inline-block; padding: 4px 8px; background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; font-family: monospace; font-size: 12px; margin: 0 4px 4px 0;">${escapeHtml(value)}</span>`;
}

function listSection(title: string, items: string[], emptyText: string, color = '#334155'): string {
  const body = items.length > 0
    ? `<ul>${items.map(item => `<li style="margin-bottom: 8px; line-height: 1.5;">${escapeHtml(item)}</li>`).join('')}</ul>`
    : `<p style="font-size: 13px; color: #94a3b8; font-style: italic;">${escapeHtml(emptyText)}</p>`;
  return `<h2>${escapeHtml(title)}</h2><div style="color: ${color};">${body}</div>`;
}

export function viewClaimPolicyContext(claim: ClaimDetails): void {
  const policyWindow = window.open('', '_blank', 'noopener,noreferrer');
  if (!policyWindow) {
    alert('Please allow popups to view policy details.');
    return;
  }

  const diagnosisCodes = claim.claim.diagnosis_codes ?? [];
  const criteriaEvaluated = [...new Set(claim.policy_evidence.map(item => item.criterion))];
  const requested = [
    ...new Set([
      ...claim.missing_information,
      ...(claim.evidence_request ? claim.evidence_request.requested_evidence.split('; ') : []),
    ]),
  ].filter(Boolean);

  const evidenceRows = claim.policy_evidence.map(item => {
    const met = item.status === 'MET';
    return `<tr>
      <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">${escapeHtml(item.criterion)}</td>
      <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0;">${escapeHtml(item.patient_value)}</td>
      <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0;">${escapeHtml(item.source)}</td>
      <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; text-align: right;">
        <span style="font-size: 10px; font-weight: 800; padding: 3px 10px; border-radius: 9999px; text-transform: uppercase; border: 1px solid ${met ? '#a7f3d0' : '#fecaca'}; background: ${met ? '#ecfdf5' : '#fef2f2'}; color: ${met ? '#047857' : '#b91c1c'};">
          ${met ? 'Met' : 'Not Met'}
        </span>
      </td>
    </tr>`;
  }).join('');

  const decisionLine = claim.decision
    ? `${escapeHtml(claim.decision.status.replace(/_/g, ' '))}${claim.decision.reason_code ? ` — ${escapeHtml(claim.decision.reason_code.replace(/_/g, ' ').toLowerCase())}` : ''}`
    : 'No decision recorded yet.';

  policyWindow.document.write(`
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>${escapeHtml(claim.policy.policy_id)} — Policy Context</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f8fafc; color: #334155; margin: 0; padding: 0; }
          header { background-color: #0f172a; color: #ffffff; padding: 24px 40px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
          .container { max-width: 900px; margin: 40px auto; background: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 10px rgb(0 0 0 / 0.05); border: 1px solid #e2e8f0; }
          h1 { margin: 0 0 8px 0; font-size: 24px; font-weight: 800; }
          h2 { font-size: 16px; font-weight: 700; color: #0284c7; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 32px; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; margin-bottom: 16px; }
          .meta-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-top: 16px; background-color: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }
          .meta-item strong { display: block; font-size: 11px; text-transform: uppercase; color: #64748b; margin-bottom: 4px; }
          .meta-item span { font-size: 14px; font-weight: 600; color: #1e293b; }
          ul, ol { padding-left: 20px; margin: 0; }
          table { width: 100%; border-collapse: collapse; font-size: 13px; }
          th { text-align: left; padding: 8px 12px; background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; }
          .footer { margin-top: 48px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 16px; }
          .btn-close { display: inline-block; margin-top: 24px; padding: 10px 20px; background-color: #0f172a; color: white; border-radius: 6px; font-weight: 600; font-size: 13px; cursor: pointer; border: none; }
          .btn-close:hover { background-color: #1e293b; }
        </style>
      </head>
      <body>
        <header>
          <div style="max-width: 900px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <span style="font-size: 11px; font-weight: 800; background-color: #0284c7; color: white; padding: 4px 8px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.05em; display: inline-block; margin-bottom: 6px;">Policy Context</span>
              <h1>${escapeHtml(claim.policy.policy_name)}</h1>
              <div style="font-size: 13px; color: #94a3b8; font-weight: 500;">
                Claim ${escapeHtml(claim.claim_id)} | Policy ID: ${escapeHtml(claim.policy.policy_id)}
              </div>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 16px; font-weight: 800; color: #0284c7;">${escapeHtml(claim.policy.payer.toUpperCase())}</div>
              <div style="font-size: 11px; color: #64748b; font-weight: bold; margin-top: 2px;">FROM LIVE CLAIM RECORD</div>
            </div>
          </div>
        </header>

        <div class="container">
          <div class="meta-grid">
            <div class="meta-item"><strong>Payer</strong><span>${escapeHtml(claim.policy.payer)}</span></div>
            <div class="meta-item"><strong>Policy ID</strong><span>${escapeHtml(claim.policy.policy_id)}</span></div>
            <div class="meta-item"><strong>Procedure</strong><span>${escapeHtml(claim.claim.procedure)} (${escapeHtml(claim.claim.procedure_code)})</span></div>
            <div class="meta-item"><strong>Agent 1 Decision</strong><span>${decisionLine}</span></div>
          </div>

          <h2>1. Coding and Identifiers</h2>
          <div style="margin-bottom: 12px;">
            <strong style="font-size: 13px; color: #64748b; display: block; margin-bottom: 6px;">Procedure Code on Claim:</strong>
            <div>${badge(claim.claim.procedure_code)}</div>
          </div>
          <div style="margin-top: 16px;">
            <strong style="font-size: 13px; color: #64748b; display: block; margin-bottom: 6px;">Diagnosis Codes on Claim:</strong>
            <div>${diagnosisCodes.length > 0 ? diagnosisCodes.map(badge).join('') : '<p style="font-size: 13px; color: #94a3b8; font-style: italic;">No diagnosis codes recorded.</p>'}</div>
          </div>

          ${listSection('2. Policy Criteria Evaluated for This Claim', criteriaEvaluated, 'No policy criteria were recorded in the claim record.')}

          <h2>3. Submitted Evidence</h2>
          ${claim.policy_evidence.length > 0
            ? `<table>
                <thead><tr><th>Criterion</th><th>Supporting Evidence</th><th>Source</th><th style="text-align: right;">Status</th></tr></thead>
                <tbody>${evidenceRows}</tbody>
              </table>`
            : '<p style="font-size: 13px; color: #94a3b8; font-style: italic;">No evidence items recorded in the claim record.</p>'}

          ${listSection('4. Information Still Requested', requested, 'No outstanding information requests for this claim.', '#991b1b')}

          <div style="text-align: center; margin-top: 30px;">
            <button class="btn-close" onclick="window.close()">Close Document Viewer</button>
          </div>

          <div class="footer">
            Rendered from the live V1 claim record. No external policy document text is available in this build; only data recorded on the claim is shown.
          </div>
        </div>
      </body>
    </html>
  `);
  policyWindow.document.close();
}
