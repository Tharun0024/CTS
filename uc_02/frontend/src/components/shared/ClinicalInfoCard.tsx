import { Stethoscope, Edit2 } from 'lucide-react';
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
          onClick={() => alert('Edit clinical details')}
          className={clsx('text-[11px] font-bold flex items-center gap-1 transition-colors', editColor)}
        >
          <Edit2 className="w-3 h-3" /> Edit
        </button>
      </div>
      <div className="px-5 py-3">
        <Row label="Diagnosis" value={claim.procedure || 'Acute Appendicitis'} highlight />
        <Row label="ICD Code" value={claim.procedure_code || 'K35.80'} mono />
        <Row label="Treatment" value={claim.procedure || 'Appendectomy'} />
        <Row label="Admission Date" value={new Date(claim.service_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} />
        <Row label="Discharge Date" value={new Date(claim.service_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} />
        <Row label="Hospital" value="Sunrise Hospital" />
        <Row label="Treating Doctor" value="Dr. Arjun Prasad" highlight />
      </div>
    </div>
  );
}
