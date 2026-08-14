import { FileText } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import type { ClaimDetails } from '../../types/claim';

interface ClaimHeaderProps {
  claim: ClaimDetails;
  backPath?: string;
  backLabel?: string;
  portal?: 'hospital' | 'insurance';
}

export function ClaimHeader({ claim, portal = 'hospital' }: ClaimHeaderProps) {
  const isHospital = portal === 'hospital';
  const accent     = isHospital ? '#059669' : '#4f46e5';
  const accentText = isHospital ? 'text-emerald-700' : 'text-indigo-700';
  const accentBg   = isHospital ? 'bg-emerald-50 border-emerald-100' : 'bg-indigo-50 border-indigo-100';
  const statusForHeader = claim.status === 'ACCEPTED' ? 'ACCEPTED' : 'REJECTED';

  return (
    <div className="glass-panel rounded-2xl mb-5 overflow-hidden animate-fade-in-up shadow-sm">
      {/* Gradient top band */}
      <div className="h-1.5 w-full" style={{ background: `linear-gradient(90deg, ${accent}, ${isHospital ? '#34d399' : '#818cf8'})` }} />

      <div className="px-6 py-5">
        <div className="flex items-center gap-5">
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border flex-shrink-0 shadow-sm ${accentBg}`}>
            <FileText className={`w-6 h-6 ${accentText}`} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3">
            <div>
              <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 mb-0.5">Claim ID</p>
              <p className={`text-[13px] leading-tight truncate font-black font-mono ${accentText}`}>
                {claim.claim_id}
              </p>
            </div>
            <div>
              <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 mb-0.5">Status</p>
              <StatusBadge status={statusForHeader} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
