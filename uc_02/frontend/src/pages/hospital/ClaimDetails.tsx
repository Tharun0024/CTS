import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';

import { ClaimHeader } from '../../components/shared/ClaimHeader';
import { PatientInfoCard } from '../../components/shared/PatientInfoCard';
import { PolicyEvidencePanel } from '../../components/shared/PolicyEvidencePanel';
import { ClaimTimeline } from '../../components/shared/ClaimTimeline';
import { ResubmissionAnalysis } from '../../components/hospital/ResubmissionAnalysis';
import { MissingInfoUploader } from '../../components/hospital/MissingInfoUploader';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';

import { getClaimDetails } from '../../services/claimsApi';
import { usePolling, isTerminalStatus } from '../../services/polling';
import type { ClaimDetails } from '../../types/claim';
import { CheckCircle2, AlertTriangle, Users, Loader2, Shield } from 'lucide-react';
import { clsx } from 'clsx';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';

export function HospitalClaimDetails() {
  const { id } = useParams<{ id: string }>();
  const [claim, setClaim]   = useState<ClaimDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState('');
  const [showResub, setShowResub] = useState(false);

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
    PROCESSING:  { icon: Loader2,       title: 'Processing Claim',            msg: 'Extracting data and running policy analysis… This page updates automatically.',  cls: 'bg-violet-50 border-violet-200',   iconCls: 'text-violet-600' },
    SUBMITTED:   { icon: Loader2,       title: 'Claim Received',              msg: 'Processing documents… Average wait: 2–3 minutes.',                               cls: 'bg-violet-50 border-violet-200',   iconCls: 'text-violet-600' },
    UNDER_REVIEW:{ icon: Loader2,       title: 'Under Review',                msg: 'Policy criteria under review…',                                                  cls: 'bg-violet-50 border-violet-200',   iconCls: 'text-violet-600' },
    ACCEPTED:    { icon: CheckCircle2,  title: 'Claim Accepted',              msg: claim.decision?.reason || '',                                                     cls: 'bg-emerald-50 border-emerald-200', iconCls: 'text-emerald-600' },
    MORE_INFO:   { icon: AlertTriangle, title: 'Additional Information Required', msg: claim.decision?.reason || '', cls: 'bg-amber-50 border-amber-200',             iconCls: 'text-amber-600' },
    HUMAN_REVIEW:{ icon: Users,         title: 'Human Review Required',       msg: claim.decision?.reason || '', cls: 'bg-blue-50 border-blue-200',                  iconCls: 'text-blue-600' },
    RESUBMISSION_CHECK:{ icon: Shield,  title: 'Resubmission Under Analysis', msg: 'Checking all criteria for resubmission eligibility…',                            cls: 'bg-indigo-50 border-indigo-200',  iconCls: 'text-indigo-600' },
    SUBMITTED_AGAIN:   { icon: CheckCircle2, title: 'Claim Resubmitted',     msg: 'Awaiting review by the insurer.',                                                 cls: 'bg-sky-50 border-sky-200',        iconCls: 'text-sky-600' },
  };

  const banner = banners[claim.status];
  const BannerIcon = banner?.icon;
  const isSpinning = ['PROCESSING','SUBMITTED','UNDER_REVIEW'].includes(claim.status);
  const handleViewPolicyDetails = () => {
    const policyWindow = window.open('', '_blank', 'noopener,noreferrer');
    if (!policyWindow) {
      alert('Please allow popups to view policy details.');
      return;
    }

    policyWindow.document.write(`
      <!doctype html>
      <html>
        <head>
          <title>Policy Details</title>
          <meta charset="utf-8" />
        </head>
        <body style="font-family: Arial, sans-serif; padding: 24px; color: #1e293b;">
          <h2 style="margin-top: 0;">${claim.policy.policy_name}</h2>
          <p><strong>Payer:</strong> ${claim.policy.payer}</p>
          <p><strong>Policy ID:</strong> ${claim.policy.policy_id}</p>
          <p><strong>Plan:</strong> ${claim.policy.payer} Secure Plus</p>
          <p><strong>Start Date:</strong> Jan 01, 2025</p>
          <p><strong>End Date:</strong> Dec 31, 2025</p>
        </body>
      </html>
    `);
    policyWindow.document.close();
  };

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <ClaimHeader claim={claim} backPath="/hospital/claims" backLabel="Back to Claims" portal="hospital" />

      {/* Status Banner */}
      {banner && (
        <div className={clsx('rounded-xl border px-5 py-3.5 mb-5 flex items-start gap-3 animate-fade-in-up shadow-sm', banner.cls)}>
          <BannerIcon className={clsx('w-5 h-5 flex-shrink-0 mt-0.5', banner.iconCls, isSpinning && 'animate-spin')} />
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-extrabold text-slate-900">{banner.title}</p>
            {banner.msg && <p className="text-[12px] text-slate-600 font-medium mt-0.5">{banner.msg}</p>}
          </div>
          {claim.status === 'ACCEPTED' && (
            <span className="flex-shrink-0 text-[11px] font-extrabold text-emerald-700 bg-emerald-100 border border-emerald-200 px-2.5 py-1 rounded-lg">
              {claim.policy_evidence.filter(e => e.status === 'MET').length}/{claim.policy_evidence.length} criteria met
            </span>
          )}
          {claim.status === 'REJECTED' && claim.resubmission.eligible && (
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
            <PatientInfoCard patient={claim.patient} portal="hospital" />
          </div>

          {claim.policy_evidence.length > 0 && (
            <PolicyEvidencePanel evidence={claim.policy_evidence} policyName={claim.policy.policy_name} portal="hospital" />
          )}

          {claim.status === 'MORE_INFO' && claim.missing_information.length > 0 && (
            <MissingInfoUploader
              claimId={claim.claim_id}
              missingItems={claim.missing_information}
              onSubmitted={() => setClaim(prev => prev ? { ...prev, status: 'SUBMITTED_AGAIN' } : prev)}
            />
          )}

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
                { label: 'Policy Plan',   value: `${claim.policy.payer} Secure Plus`, accent: false },
                { label: 'Start Date',    value: 'Jan 01, 2025',       accent: false },
                { label: 'End Date',      value: 'Dec 31, 2025',       accent: false },
              ].map(r => (
                <div key={r.label} className="flex items-baseline justify-between border-b border-slate-50 pb-2 last:border-0 last:pb-0">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{r.label}</span>
                  <span className={clsx('text-[13px] font-bold', r.accent ? 'text-emerald-700' : 'text-slate-800')}>{r.value}</span>
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
    </div>
  );
}
