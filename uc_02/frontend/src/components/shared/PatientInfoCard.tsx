import { useEffect, useState } from 'react';
import { User, Edit2 } from 'lucide-react';
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
  const [editablePatient, setEditablePatient] = useState({
    name: patient.name || 'Ramesh Kumar',
    age: patient.age || 46,
    gender: patient.gender || 'Male',
    contact: '98765 43210',
    address: 'Coimbatore, Tamil Nadu',
  });

  useEffect(() => {
    setEditablePatient({
      name: patient.name || 'Ramesh Kumar',
      age: patient.age || 46,
      gender: patient.gender || 'Male',
      contact: '98765 43210',
      address: 'Coimbatore, Tamil Nadu',
    });
  }, [patient]);

  const handleEdit = () => {
    const nextName = window.prompt('Patient name', editablePatient.name);
    if (nextName === null) return;

    const nextAgeRaw = window.prompt('Patient age', String(editablePatient.age));
    if (nextAgeRaw === null) return;

    const parsedAge = Number.parseInt(nextAgeRaw, 10);
    if (!Number.isFinite(parsedAge) || parsedAge <= 0) {
      alert('Please enter a valid age.');
      return;
    }

    const nextGender = window.prompt('Patient gender', editablePatient.gender);
    if (nextGender === null) return;

    const nextContact = window.prompt('Contact number', editablePatient.contact);
    if (nextContact === null) return;

    const nextAddress = window.prompt('Address', editablePatient.address);
    if (nextAddress === null) return;

    setEditablePatient({
      name: nextName.trim() || editablePatient.name,
      age: parsedAge,
      gender: nextGender.trim() || editablePatient.gender,
      contact: nextContact.trim() || editablePatient.contact,
      address: nextAddress.trim() || editablePatient.address,
    });
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
      {/* Rows */}
      <div className="px-5 py-3">
        <Row label="Name"          value={editablePatient.name} />
        <Row label="Age / Gender"  value={`${editablePatient.age} / ${editablePatient.gender}`} />
        <Row label="Policy No."    value={patient.patient_id} mono />
        <Row label="Policy Holder" value={editablePatient.name} />
        <Row label="Relationship"  value="Self" />
        <Row label="Contact"       value={editablePatient.contact} />
        <Row label="Address"       value={editablePatient.address} />
      </div>
    </div>
  );
}
