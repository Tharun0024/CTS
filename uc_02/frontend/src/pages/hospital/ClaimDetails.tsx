import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';

import { ClaimHeader } from '../../components/shared/ClaimHeader';
import { PatientInfoCard } from '../../components/shared/PatientInfoCard';
import { PolicyEvidencePanel } from '../../components/shared/PolicyEvidencePanel';
import { ClaimTimeline } from '../../components/shared/ClaimTimeline';
import { ResubmissionAnalysis } from '../../components/hospital/ResubmissionAnalysis';
import { MissingInfoUploader } from '../../components/hospital/MissingInfoUploader';
import { ProviderDecisionPanel } from '../../components/hospital/ProviderDecisionPanel';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';

import { getClaimDetails } from '../../services/claimsApi';
import { PolicyModal } from '../../components/shared/PolicyModal';
import { HumanReviewWorkspace } from '../../components/shared/HumanReviewWorkspace';
import { HospitalHumanResolutionPanel } from '../../components/hospital/HospitalHumanResolutionPanel';
import { PriorAuthStatusCard } from '../../components/shared/PriorAuthStatusCard';
import { AgentConfidenceCard } from '../../components/shared/AgentConfidenceCard';
import { DecisionChain } from '../../components/shared/DecisionChain';
import { decisionLabel } from '../../utils/decisionHumanizer';
import { usePolling, isTerminalStatus } from '../../services/polling';
import type { ClaimDetails, ClaimVersion } from '../../types/claim';
import { CheckCircle2, AlertTriangle, Users, Loader2, Shield, Clock } from 'lucide-react';
import { clsx } from 'clsx';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';

export function HospitalClaimDetails() {
  const { id } = useParams<{ id: string }>();
  const [claim, setClaim] = useState<ClaimDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showResub, setShowResub] = useState(false);
  const [isPolicyOpen, setIsPolicyOpen] = useState(false);

  const fetchClaim = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getClaimDetails(id);
      setClaim(data);
      if (loading) setLoading(false);
    } catch {
      setError('Failed to load claim details.');
      setLoading(false);
    }
  }, [id, loading]);

  useEffect(() => { fetchClaim(); }, [id]);

  usePolling(
    () => getClaimDetails(id!),
    (data) => setClaim(data),
    (data) => isTerminalStatus(data.status),
    5000,
    !!id && !!claim && !isTerminalStatus(claim.status)
  );

  if (loading) return (
    <LoadingState message="Loading claim details…" fullPage />
  );
  if (error || !claim) return (
    <ErrorState message={error || 'Claim not found.'} onRetry={fetchClaim} />
  );

  /* Status banners config */
  const banners: Record<string, { icon: any; title: string; msg: string; cls: string; iconCls: string }> = {
    PROCESSING: { icon: Loader2, title: 'Processing Claim', msg: 'Extracting data and running policy analysis… This page updates automatically.', cls: 'bg-violet-50 border-violet-200', iconCls: 'text-violet-600' },
    SUBMITTED: { icon: Loader2, title: 'Claim Received', msg: 'Processing documents… Average wait: 2–3 minutes.', cls: 'bg-violet-50 border-violet-200', iconCls: 'text-violet-600' },
    UNDER_REVIEW: { icon: Loader2, title: 'Under Review', msg: 'Policy criteria under review…', cls: 'bg-violet-50 border-violet-200', iconCls: 'text-violet-600' },
    ACCEPTED: { icon: CheckCircle2, title: 'APPROVE', msg: claim.decision?.reason || '', cls: 'bg-emerald-50 border-emerald-200', iconCls: 'text-emerald-600' },
    REJECTED: { icon: AlertTriangle, title: 'REJECT', msg: claim.decision?.reason || '', cls: 'bg-red-50 border-red-200', iconCls: 'text-red-600' },
    MORE_INFO: { icon: AlertTriangle, title: 'MORE INFORMATION REQUIRED', msg: claim.decision?.reason || '', cls: 'bg-amber-50 border-amber-200', iconCls: 'text-amber-600' },
    HUMAN_REVIEW: { icon: Users, title: 'HUMAN REVIEW', msg: claim.decision?.reason || '', cls: 'bg-blue-50 border-blue-200', iconCls: 'text-blue-600' },
    RESUBMISSION_CHECK: { icon: Shield, title: 'Resubmission Under Analysis', msg: 'Checking all criteria for resubmission eligibility…', cls: 'bg-indigo-50 border-indigo-200', iconCls: 'text-indigo-600' },
    SUBMITTED_AGAIN: { icon: CheckCircle2, title: 'Claim Resubmitted', msg: 'Awaiting review by the insurer.', cls: 'bg-sky-50 border-sky-200', iconCls: 'text-sky-655' },
  };

  const banner = banners[claim.status];
  const BannerIcon = banner?.icon;
  const isSpinning = ['PROCESSING', 'SUBMITTED', 'UNDER_REVIEW'].includes(claim.status);

  const versionsForView: ClaimVersion[] = (claim.versions && claim.versions.length > 0)
    ? claim.versions
    : [{
      version: 'V1',
      attempt: 1,
      decision: claim.decision
        ? { status: claim.decision.status, reason: claim.decision.reason, reason_code: claim.decision.reason_code }
        : null,
    }];
  const versionStatusCls: Record<string, string> = {
    ACCEPT: 'text-emerald-600',
    REJECT: 'text-red-600',
    MORE_INFORMATION: 'text-amber-600',
    HUMAN_REVIEW: 'text-blue-600',
  };

  const handleViewPolicyDetails = () => {
    setIsPolicyOpen(true);
  };

  const requiredEvidencePaths = claim.decision?.criterion_assessments
    ? Object.values(claim.decision.criterion_assessments)
      .flatMap((a: any) => a.required_evidence_paths || [])
      .filter(Boolean)
    : [];

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <ClaimHeader claim={claim} backPath="/hospital/claims" backLabel="Back to Claims" portal="hospital" />

      {/* Decision Flow Chain */}
      <DecisionChain claim={claim} />

      {/* Status Banner */}
      {banner && (
        <div className={clsx('rounded-xl border px-5 py-3.5 mb-5 flex items-start gap-3 animate-fade-in-up shadow-sm', banner.cls)}>
          <BannerIcon className={clsx('w-5 h-5 flex-shrink-0 mt-0.5', banner.iconCls, isSpinning && 'animate-spin')} />
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-extrabold text-slate-900">{banner.title}</p>
            {banner.msg && <p className="text-[12px] text-slate-605 font-medium mt-0.5 whitespace-pre-wrap">{banner.msg}</p>}
          </div>
          {claim.status === 'ACCEPTED' && (
            <span className="flex-shrink-0 text-[11px] font-extrabold text-emerald-700 bg-emerald-100 border border-emerald-200 px-2.5 py-1 rounded-lg">
              {(claim.policy_evidence || []).filter(e => e.status === 'MET').length}/{(claim.policy_evidence || []).length} criteria met
            </span>
          )}
          {claim.status === 'REJECTED' && claim.resubmission?.eligible && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowResub(v => !v)}
              className="text-emerald-700 border-emerald-200 bg-emerald-50 hover:bg-emerald-100 flex-shrink-0"
            >
              {showResub ? 'Hide Analysis' : 'View Resubmission Analysis →'}
            </Button>
          )}
        </div>
      )}

      {/* 3-column layout */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Left 2 cols */}
        <div className="xl:col-span-2 space-y-5">
          <div className="grid grid-cols-1 gap-5">
            <PatientInfoCard patient={claim.patient || { patient_id: 'UNKNOWN', age: 0, gender: 'Unknown' }} portal="hospital" />
          </div>

          {/* V1 Workflow Details */}
          <Card className="animate-fade-in-up shadow-sm">
            <CardHeader className="py-3 px-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <CardTitle className="text-xs font-black uppercase tracking-wider flex items-center gap-2">
                <Shield className="w-3.5 h-3.5 text-emerald-600" />
                V1 Workflow Execution & Evidence
              </CardTitle>
              <span className="text-[10px] font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                Attempt {claim.attempt ?? 1} of 2
              </span>
            </CardHeader>
            <CardContent className="p-5 space-y-6">

              {claim.status === 'MORE_INFO' || claim.evidence_request ? (
                <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-4.5 space-y-4">
                  <div className="flex items-center justify-between border-b border-amber-200 pb-2">
                    <h4 className="text-[12px] font-black text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      MORE INFORMATION REQUIRED
                    </h4>
                    <span className="text-[9px] font-extrabold bg-amber-100 text-amber-800 border border-amber-200 px-2.5 py-0.5 rounded-full">
                      {claim.evidence_request?.status.replace(/_/g, ' ') || 'AWAITING RESPONSE'}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="space-y-3">
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Requested Evidence</span>
                        <p className="font-extrabold text-slate-900 mt-0.5">{claim.evidence_request?.requested_evidence || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide font-sans">Agent 1 Reasoning</span>
                        <div className="font-medium text-slate-700 mt-0.5 space-y-1 bg-white p-2.5 rounded-lg border border-slate-100 max-h-40 overflow-y-auto font-mono text-[11px] leading-relaxed">
                          {claim.decision?.reasoning && claim.decision.reasoning.length > 0 ? (
                            claim.decision.reasoning.map((r, i) => <p key={i}>{r}</p>)
                          ) : (
                            <p>{claim.decision?.reason || 'No specific reasoning trace provided.'}</p>
                          )}
                        </div>
                      </div>
                      {claim.decision?.criterion_assessments && (
                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Required Evidence Paths</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {requiredEvidencePaths.map((path, idx) => (
                              <span key={idx} className="font-mono text-[10px] bg-white text-slate-800 px-2 py-0.5 rounded border border-slate-150 shadow-sm">
                                {path}
                              </span>
                            ))}
                            {requiredEvidencePaths.length === 0 && (
                              <span className="text-slate-405 italic">None recorded.</span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="space-y-3">
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Agent 2 Recovery Status</span>
                        <div className="mt-0.5 p-2.5 bg-white rounded-lg border border-slate-100 text-[11px] font-medium text-slate-700 space-y-1.5 shadow-sm">
                          {claim.agent2_invoked ? (
                            <>
                              <p className="font-extrabold text-indigo-700 flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                                Agent 2 Recovery Invoked
                              </p>
                              {claim.recovery_result?.recovered_evidence_ids && claim.recovery_result.recovered_evidence_ids.length > 0 ? (
                                <p>Recovered Evidence: <span className="font-mono bg-indigo-50 px-1 py-0.2 rounded border border-indigo-100">{claim.recovery_result.recovered_evidence_ids.join(', ')}</span></p>
                              ) : (
                                <p className="text-slate-400 italic">No releasable evidence recovered by Agent 2 yet.</p>
                              )}
                              {claim.recovery_result?.notes && claim.recovery_result.notes.map((note, idx) => (
                                <p key={idx} className="text-slate-500 italic text-[10px]">• {note}</p>
                              ))}
                            </>
                          ) : (
                            <p className="text-slate-400 italic">Agent 2 Recovery not invoked / not available.</p>
                          )}
                        </div>
                      </div>

                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Provider Resubmission Status</span>
                        <div className="mt-0.5 p-2.5 bg-white rounded-lg border border-slate-100 text-[11px] font-medium text-slate-700 space-y-1.5 shadow-sm">
                          <p>Status: <span className="font-extrabold text-slate-900 uppercase">{claim.resubmission_status || claim.resubmission?.status || 'NOT REQUIRED'}</span></p>
                          {claim.provider_decisions && claim.provider_decisions.length > 0 ? (
                            <div className="border-t border-slate-100 pt-1.5 mt-1.5 space-y-1">
                              <p className="font-bold text-slate-800">Hospital Provider Decisions:</p>
                              {claim.provider_decisions.map((d, i) => (
                                <p key={i} className="text-[10px] border-b border-slate-50 pb-1 last:border-0">
                                  <span className={`font-black px-1 rounded ${d.decision === 'ACCEPT' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-rose-50 text-rose-700 border border-rose-100'}`}>{d.decision}</span> on {d.decided_at ? new Date(d.decided_at).toLocaleString() : 'N/A'}
                                  {d.reason && <span className="text-slate-404 italic block mt-0.5">Reason: {d.reason}</span>}
                                </p>
                              ))}
                            </div>
                          ) : (
                            <p className="text-slate-404 italic">No provider consent decisions recorded.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-slate-50 border border-slate-205 border-dashed rounded-xl p-4 flex flex-col items-center justify-center text-center">
                    <Clock className="w-6 h-6 text-slate-350 mb-2" />
                    <p className="text-xs font-semibold text-slate-500">No Evidence Request</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">This claim has not requested additional clinical documents.</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-205 border-dashed rounded-xl p-4 flex flex-col items-center justify-center text-center">
                    <Clock className="w-6 h-6 text-slate-350 mb-2" />
                    <p className="text-xs font-semibold text-slate-500">No Evidence Uploaded</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">Awaiting provider clinical data release.</p>
                  </div>
                </div>
              )}

              {/* 4. Attempt / Resubmission visual timeline — real versions */}
              <div className="border-t border-slate-100 pt-4 space-y-3">
                <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-wider">Submissions & Attempts</h4>

                <div className="flex flex-col sm:flex-row items-stretch gap-4 justify-between">
                  {versionsForView.map((v, idx) => {
                    const attemptNo = v.attempt ?? idx + 1;
                    const delta = v.new_evidence_delta ?? [];
                    return (
                      <div key={`${v.version}-${attemptNo}`} className="flex-1 bg-slate-50/50 border border-slate-200 rounded-xl p-3 flex flex-col justify-between">
                        <div>
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-xs font-bold text-slate-900">Attempt {attemptNo} · {v.version}</span>
                            <span className="text-[10px] font-bold text-slate-500">{idx === versionsForView.length - 1 ? 'Latest' : 'Completed'}</span>
                          </div>
                          <div className="flex flex-col items-center py-2 text-center text-xs space-y-1 bg-white border border-slate-150 rounded-lg p-2.5">
                            {v.decision ? (
                              <>
                                <span className={clsx('font-extrabold font-mono text-[10px]', versionStatusCls[v.decision.status] ?? 'text-slate-600')}>
                                  {decisionLabel(v.decision.status)}
                                </span>
                                <span className="text-slate-400 text-[10px]">↓</span>
                                <span className="font-medium text-slate-600 text-[10px] leading-snug">{v.decision.reason}</span>
                              </>
                            ) : (
                              <span className="font-semibold text-slate-500">Decision pending…</span>
                            )}
                            {delta.length > 0 && (
                              <span className="font-semibold text-emerald-700 text-[10px]">+{delta.length} new evidence item(s)</span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}

                  {/* Next attempt placeholder until a resubmission exists */}
                  {(claim.attempt ?? 1) < 2 && versionsForView.length < 2 && (
                    <div className="flex-1 border border-dashed border-slate-200 rounded-xl p-3 flex items-center justify-center text-center">
                      <div>
                        <span className="text-xs font-bold text-slate-400 block">Attempt 2</span>
                        <span className="text-[10px] text-slate-355 mt-1 block">Awaiting resubmission path</span>
                      </div>
                    </div>
                  )}
                </div>

              </div>

            </CardContent>
          </Card>

          {(claim.policy_evidence || []).length > 0 && (
            <PolicyEvidencePanel evidence={claim.policy_evidence} policyName={claim.policy?.policy_name || 'Policy on file'} policyId={claim.policy?.policy_id} portal="hospital" onViewPolicy={handleViewPolicyDetails} />
          )}

          {(claim.status === 'HUMAN_REVIEW' || claim.workflow_state === 'HUMAN_REVIEW') && (
            <>
              <HumanReviewWorkspace claim={claim} portal="hospital" />
              <HospitalHumanResolutionPanel claim={claim} onResolved={fetchClaim} />
            </>
          )}

          {claim.status === 'MORE_INFO' && (claim.missing_information || []).length > 0 && (
            <MissingInfoUploader
              claimId={claim.claim_id}
              missingItems={claim.missing_information}
              onSubmitted={() => setClaim(prev => prev ? { ...prev, status: 'SUBMITTED_AGAIN' } : prev)}
            />
          )}

          {/* Provider ACCEPT/DECLINE consent on Agent 2 recovered evidence */}
          <ProviderDecisionPanel claim={claim} onDecided={fetchClaim} />

          {(claim.status === 'RESUBMISSION_CHECK' || showResub) && (
            <ResubmissionAnalysis
              claimId={claim.claim_id}
              onResubmitted={() => setClaim(prev => prev ? { ...prev, status: 'SUBMITTED_AGAIN' } : prev)}
            />
          )}
        </div>

        {/* Right column */}
        <div className="space-y-5">
          {claim.timeline && <ClaimTimeline events={claim.timeline} portal="hospital" />}

          {/* Phase 4: persisted Phase 1 pre-check + Phase 2 confidence, read from the authoritative claim record */}
          <PriorAuthStatusCard claim={claim} portal="hospital" />
          <AgentConfidenceCard claim={claim} />

          {/* Policy Reference Card */}
          <Card className="animate-fade-in-up stagger-2">
            <CardHeader className="py-3 px-5 border-b border-slate-100 bg-slate-50/50">
              <CardTitle className="text-[12px] font-extrabold uppercase tracking-wider flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center">
                  <Shield className="w-3.5 h-3.5 text-emerald-600" />
                </div>
                Policy Reference
              </CardTitle>
            </CardHeader>
            <CardContent className="px-5 py-4 space-y-3">
              {[
                { label: 'Payer', value: claim.policy?.payer },
                { label: 'Policy ID', value: claim.policy?.policy_id },
                { label: 'Policy Name', value: claim.policy?.policy_name },
                { label: 'Procedure Code', value: claim.claim?.procedure_code },
              ].map(r => (
                <div key={r.label} className="flex items-baseline justify-between border-b border-slate-50 pb-2 last:border-0 last:pb-0">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{r.label}</span>
                  <span className="text-[13px] font-bold text-slate-800">{r.value || 'N/A'}</span>
                </div>
              ))}
              <button
                onClick={handleViewPolicyDetails}
                className="text-[12px] font-bold text-emerald-700 hover:text-emerald-900 mt-2 flex items-center gap-1 transition-colors"
              >
                View full policy →
              </button>
            </CardContent>
          </Card>

        </div>
      </div>
      {claim && (
        <PolicyModal
          isOpen={isPolicyOpen}
          onClose={() => setIsPolicyOpen(false)}
          policyId={claim.policy?.policy_id}
          claim={claim}
        />
      )}
    </div>
  );
}
