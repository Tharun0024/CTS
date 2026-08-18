import { ArrowRight, Shield, Brain, Sparkles, UserCheck, CheckCircle2, AlertCircle } from 'lucide-react';
import type { ClaimDetails } from '../../types/claim';
import { clsx } from 'clsx';
import { decisionLabel } from '../../utils/decisionHumanizer';
import { Card, CardContent } from '../ui/Card';

interface DecisionChainProps {
  claim: ClaimDetails;
}

export function DecisionChain({ claim }: DecisionChainProps) {
  // 1. Prior Auth Node
  const precheck = claim.prior_auth_precheck;
  const paRequired = precheck ? !!precheck.requires_prior_auth : false;
  const paLabel = precheck 
    ? (paRequired ? 'PA REQUIRED' : 'PA NOT REQUIRED') 
    : 'PA NOT REQUIRED';
  const paColor = paRequired ? 'bg-sky-50 text-sky-700 border-sky-200' : 'bg-slate-50 text-slate-600 border-slate-200';

  // 2. Agent 1 Decision Node
  const a1Status = claim.original_rejection 
    ? 'REJECT' 
    : (claim.decision ? decisionLabel(claim.decision.status) : 'PENDING');
  
  let a1Color = 'bg-slate-50 text-slate-600 border-slate-200';
  if (a1Status === 'APPROVE' || a1Status === 'APPROVED') {
    a1Color = 'bg-emerald-50 text-emerald-700 border-emerald-250';
  } else if (a1Status === 'REJECT' || a1Status === 'REJECTED') {
    a1Color = 'bg-red-50 text-red-750 border-red-250';
  } else if (a1Status.includes('INFORMATION')) {
    a1Color = 'bg-amber-50 text-amber-700 border-amber-250';
  } else if (a1Status === 'HUMAN REVIEW') {
    a1Color = 'bg-blue-50 text-blue-700 border-blue-250';
  }

  // 3. Confidence Node
  const confLevel = claim.original_rejection
    ? claim.original_rejection.confidence_level
    : (claim.decision ? claim.decision.confidence_level : null);
  const confScore = claim.original_rejection
    ? claim.original_rejection.confidence_score
    : (claim.decision ? claim.decision.confidence_score : null);
  const confLabel = confLevel 
    ? `${confLevel} (${typeof confScore === 'number' ? Math.round(confScore * 100) : 0}%)`
    : 'N/A';
  let confColor = 'bg-slate-50 text-slate-600 border-slate-200';
  if (confLevel === 'HIGH') {
    confColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  } else if (confLevel === 'MEDIUM') {
    confColor = 'bg-amber-50 text-amber-700 border-amber-200';
  } else if (confLevel === 'LOW') {
    confColor = 'bg-rose-50 text-rose-700 border-rose-200';
  }

  // 4. Human Verification Node
  const hasHV = claim.workflow_state === 'HUMAN_REVIEW' || !!claim.human_verification_pending || !!claim.human_resolution;
  const hvResolved = !!claim.human_resolution;
  const hvLabel = hasHV 
    ? (hvResolved ? 'VERIFIED' : 'PENDING') 
    : 'NOT REQUIRED';
  const hvColor = hasHV
    ? (hvResolved ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse')
    : 'bg-slate-50 text-slate-400 border-slate-200';

  // 5. Final Decision Node
  const finalStatus = claim.status;
  const finalLabel = finalStatus === 'ACCEPTED' 
    ? 'APPROVED' 
    : (finalStatus === 'REJECTED' ? 'REJECTED' : 'PENDING');
  const finalColor = finalStatus === 'ACCEPTED'
    ? 'bg-emerald-600 text-white border-emerald-600'
    : (finalStatus === 'REJECTED' ? 'bg-rose-600 text-white border-rose-600' : 'bg-slate-100 text-slate-700 border-slate-300');

  const steps = [
    { label: 'Prior Auth', value: paLabel, color: paColor, icon: Shield },
    { label: 'Agent 1 Decision', value: a1Status, color: a1Color, icon: Brain },
    { label: 'Confidence', value: confLabel, color: confColor, icon: Sparkles },
    { label: 'Human Verification', value: hvLabel, color: hvColor, icon: UserCheck },
    { label: 'Final Decision', value: finalLabel, color: finalColor, icon: finalStatus === 'ACCEPTED' ? CheckCircle2 : AlertCircle },
  ];

  return (
    <Card className="glass-panel border-slate-200 rounded-2xl overflow-hidden shadow-sm mb-5">
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50">
        <h3 className="text-xs font-black uppercase tracking-wider text-slate-700">Decision Flow Chain</h3>
      </div>
      <CardContent className="p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 relative">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div key={idx} className="flex-1 flex flex-col md:flex-row items-center gap-3">
                <div className="flex flex-col items-center md:items-start flex-1 text-center md:text-left">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5 mb-1">
                    <Icon className="w-3.5 h-3.5" />
                    {step.label}
                  </span>
                  <span className={clsx(
                    'text-[11px] font-extrabold px-3 py-1 rounded-xl border tracking-wide uppercase',
                    step.color
                  )}>
                    {step.value}
                  </span>
                </div>
                {idx < steps.length - 1 && (
                  <ArrowRight className="w-5 h-5 text-slate-300 hidden md:block rotate-0" />
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
