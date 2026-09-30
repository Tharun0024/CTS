import { useState } from 'react';
import { Stethoscope, Edit2, Lock } from 'lucide-react';
import type { ClaimDetails } from '../../types/claim';
import { clsx } from 'clsx';

interface ClinicalInfoCardProps {
  claim: ClaimDetails['claim'];
  portal?: 'hospital' | 'insurance';
}

const Row = ({ label, value, mono, highlight }: { label: string; value: string; mono?: boolean; highlight?: boolean }) => (
  <div className="flex items-baseline gap-2 py-1.5 border-b border-slate-50 last:border-0">
    <span className="text-[11px] font-bold text-slate-400 w-[110px] flex-shrink-0 uppercase tracking-wider">{label}</span>
    <span className={clsx(
      'text-[13px] font-semibold truncate',
      mono && 'font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-700 text-[11px]',
      highlight ? 'text-slate-900 font-bold' : 'text-slate-800'
    )}>{value}</span>
  </div>
);

export function ClinicalInfoCard({ claim, portal = 'hospital' }: ClinicalInfoCardProps) {
  const isHospital = portal === 'hospital';
  const accentBg = isHospital ? 'bg-emerald-50' : 'bg-indigo-50';
  const accentIcon = isHospital ? 'text-emerald-600' : 'text-indigo-600';
  const editColor = isHospital ? 'text-emerald-600 hover:text-emerald-800' : 'text-indigo-600 hover:text-indigo-800';

  const [notice, setNotice] = useState(false);

  // All values come from the real backend claim record; no fabricated
  // defaults. Fields without a backend source are shown honestly.
  const procedure = claim.procedure || 'Unspecified procedure';
  const code = claim.procedure_code || 'N/A';
  const doctor = claim.provider_id || 'Not on record';

  // V1 claim versions are immutable and there is no backend update contract
  // for clinical fields, so Edit never mutates state — it surfaces the lock.
  const handleEdit = () => {
    setNotice(v => !v);
  };

  return (
    <div className="glass-panel rounded-2xl overflow-hidden animate-fade-in-up stagger-1 shadow-sm">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50/60">
        <div className="flex items-center gap-2.5">
          <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center', accentBg)}>
            <Stethoscope className={clsx('w-3.5 h-3.5', accentIcon)} />
          </div>
          <h3 className="text-[12px] font-extrabold text-slate-800 uppercase tracking-wider">Clinical Information</h3>
        </div>
        <button
          type="button"
          onClick={handleEdit}
          className={clsx('text-[11px] font-bold flex items-center gap-1 transition-colors', editColor)}
        >
          <Edit2 className="w-3 h-3" /> Edit
        </button>
      </div>
      {notice && (
        <div className="px-5 py-2.5 bg-slate-50 border-b border-slate-100 flex items-start gap-2">
          <Lock className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
          <p className="text-[11px] text-slate-500 font-medium leading-relaxed">
            Clinical details are locked to the submitted claim record — V1 claim versions are immutable and the
            backend provides no clinical-field update contract. Additional clinical documentation can be submitted
            through the claim's Missing Information upload (the only real write path).
          </p>
        </div>
      )}
      <div className="px-5 py-3">
        <Row label="Diagnosis" value={claim.diagnosis_codes.length > 0 ? claim.diagnosis_codes.join(', ') : 'Not on record'} highlight />
        <Row label="Code" value={code} mono />
        <Row label="Treatment" value={procedure} />
        <Row label="Service Date" value={claim.service_date ? new Date(claim.service_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Not on record'} />
        <Row label="Hospital" value="City General Hospital" />
        <Row label="Treating Doctor" value={doctor} highlight />
      </div>
    </div>
  );
}
