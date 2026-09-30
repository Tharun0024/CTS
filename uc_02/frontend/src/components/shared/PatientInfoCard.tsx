import { useState } from 'react';
import { User, Edit2, Lock } from 'lucide-react';
import type { ClaimDetails } from '../../types/claim';
import { clsx } from 'clsx';

interface PatientInfoCardProps {
  patient: ClaimDetails['patient'];
  portal?: 'hospital' | 'insurance';
}

const Row = ({ label, value, mono }: { label: string; value: string; mono?: boolean }) => (
  <div className="flex items-baseline gap-2 py-1.5 border-b border-slate-50 last:border-0">
    <span className="text-[11px] font-bold text-slate-400 w-[110px] flex-shrink-0 uppercase tracking-wider">{label}</span>
    <span className={clsx('text-[13px] font-semibold text-slate-800 truncate', mono && 'font-mono')}>{value}</span>
  </div>
);

export function PatientInfoCard({ patient, portal = 'hospital' }: PatientInfoCardProps) {
  const isHospital = portal === 'hospital';
  const accentBg   = isHospital ? 'bg-emerald-50' : 'bg-indigo-50';
  const accentIcon = isHospital ? 'text-emerald-600' : 'text-indigo-600';
  const editColor  = isHospital ? 'text-emerald-600 hover:text-emerald-800' : 'text-indigo-600 hover:text-indigo-800';
  const [notice, setNotice] = useState(false);

  // Display values come ONLY from the real backend claim record. Fields with
  // no backend source are shown honestly as "Not on record".
  const displayName = patient.name || patient.patient_id;
  const displayAge = patient.age > 0 ? String(patient.age) : 'Not on record';
  const displayGender = patient.gender && patient.gender !== 'Unknown' ? patient.gender : 'Not on record';
  const displayDob = patient.dob || 'Not on record';
  const displayRelationship = patient.relationship || 'Not on record';
  const displayContact = patient.contact || 'Not on record';
  const displayAddress = patient.address || 'Not on record';
  const displayPolicyHolder = patient.policy_holder || displayName;

  // V1 claim versions are immutable and the backend exposes no patient-update
  // contract, so Edit never mutates local state — it explains the real path
  // (additional documentation via the claim's missing-information upload).
  const handleEdit = () => {
    setNotice(v => !v);
  };

  return (
    <div className="glass-panel rounded-2xl overflow-hidden animate-fade-in-up shadow-sm">
      {/* Card header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50/60">
        <div className="flex items-center gap-2.5">
          <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center', accentBg)}>
            <User className={clsx('w-3.5 h-3.5', accentIcon)} />
          </div>
          <h3 className="text-[12px] font-extrabold text-slate-800 uppercase tracking-wider">Patient Information</h3>
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
            Patient details are locked to the submitted claim record — V1 claim versions are immutable and the
            backend provides no patient-field update contract. To add supporting information, use the
            Missing Information upload on this claim (the only real write path).
          </p>
        </div>
      )}
      {/* Rows */}
      <div className="px-5 py-3">
        <Row label="Name"          value={displayName} />
        <Row label="Age / Gender"  value={`${displayAge} / ${displayGender}`} />
        <Row label="DOB"           value={displayDob} />
        <Row label="Policy No."    value={patient.patient_id} mono />
        <Row label="Policy Holder" value={displayPolicyHolder} />
        <Row label="Relationship"  value={displayRelationship} />
        <Row label="Contact"       value={displayContact} />
        <Row label="Address"       value={displayAddress} />
      </div>
    </div>
  );
}
