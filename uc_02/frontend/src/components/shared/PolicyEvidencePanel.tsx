import { Shield, CheckCircle2, XCircle, AlertTriangle, ExternalLink } from 'lucide-react';
import type { PolicyEvidenceItem } from '../../types/claim';
import { clsx } from 'clsx';

interface PolicyEvidencePanelProps {
  evidence: PolicyEvidenceItem[];
  policyName: string;
  policyId?: string;
  portal?: 'hospital' | 'insurance';
  // Opens the real policy context viewer (derived from the live claim record).
  onViewPolicy?: () => void;
}

export function PolicyEvidencePanel({ evidence, policyName, policyId, portal = 'hospital', onViewPolicy }: PolicyEvidencePanelProps) {
  const isHospital = portal === 'hospital';
  const accentBg   = isHospital ? 'bg-emerald-50' : 'bg-indigo-50';
  const accentIcon = isHospital ? 'text-emerald-600' : 'text-indigo-600';
  const linkColor  = isHospital ? 'text-emerald-700 hover:text-emerald-900 bg-emerald-50 hover:bg-emerald-100 border-emerald-100' : 'text-indigo-700 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 border-indigo-100';
  const rowHover   = isHospital ? 'hover:bg-emerald-50/30' : 'hover:bg-indigo-50/30';

  // Real evidence only — no fabricated fallback rows.
  const finalItems = evidence;

  const metCount = finalItems.filter(i => i.status === 'MET').length;
  void policyId;

  return (
    <div className="glass-panel rounded-2xl overflow-hidden animate-fade-in-up shadow-sm">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/60 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-3 flex-1">
          <div className={clsx('w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0', accentBg)}>
            <Shield className={clsx('w-4 h-4', accentIcon)} />
          </div>
          <div>
            <h3 className="text-[12px] font-extrabold text-slate-800 uppercase tracking-wider">Policy Analysis</h3>
            <p className="text-[11px] text-slate-400 font-medium mt-0.5">{policyName}</p>
          </div>
        </div>

        {/* Progress */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-[11px]">
            <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /><span className="text-slate-500 font-semibold">Met</span></div>
            <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /><span className="text-slate-500 font-semibold">Not Met</span></div>
            <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /><span className="text-slate-500 font-semibold">Pending</span></div>
          </div>
          {onViewPolicy && (
            <button
              onClick={onViewPolicy}
              className={clsx('inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-lg border transition-colors', linkColor)}
            >
              View Policy <ExternalLink className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Score bar */}
      <div className="px-5 py-3 bg-white/60 border-b border-slate-100 flex items-center gap-4">
        <span className="text-[11px] font-bold text-slate-500">{metCount}/{finalItems.length} criteria satisfied</span>
        <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-600 transition-all duration-700"
            style={{ width: `${finalItems.length > 0 ? (metCount / finalItems.length) * 100 : 0}%` }}
          />
        </div>
        <span className="text-[11px] font-extrabold text-emerald-700">{finalItems.length > 0 ? Math.round((metCount / finalItems.length) * 100) : 0}%</span>
      </div>

      {finalItems.length === 0 ? (
        <div className="px-5 py-10 text-center">
          <AlertTriangle className="w-6 h-6 text-slate-300 mx-auto mb-2" />
          <p className="text-[12px] font-semibold text-slate-500">No policy evidence recorded for this claim.</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Evidence rows appear here once the backend records submitted evidence items.</p>
        </div>
      ) : (
      /* Table */
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[13px] min-w-[480px]">
          <thead className="bg-slate-50/80 border-b border-slate-100 text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">
            <tr>
              <th className="px-5 py-3 w-[200px]">Criterion</th>
              <th className="px-5 py-3">Supporting Evidence</th>
              <th className="px-5 py-3 text-right w-[130px]">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50 bg-white/70">
            {finalItems.map((item, idx) => {
              const isMet = item.status === 'MET';
              return (
                <tr key={idx} className={clsx('transition-colors', rowHover)}>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      {isMet
                        ? <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        : <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                      }
                      <span className="font-bold text-slate-800">{item.criterion}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-slate-500 font-medium leading-relaxed">{item.patient_value}</td>
                  <td className="px-5 py-3.5 text-right">
                    <span className={clsx('text-[9px] font-extrabold px-2.5 py-1 rounded-full uppercase tracking-wider border inline-block',
                      isMet ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200'
                    )}>
                      {isMet ? '✓ Met' : '✗ Not Met'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      )}
    </div>
  );
}
