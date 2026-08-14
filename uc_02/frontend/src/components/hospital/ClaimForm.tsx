import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, X, CheckCircle2 } from 'lucide-react';
import { DocumentUploader } from './DocumentUploader';
import { createClaim } from '../../services/claimsApi';
import type { CreateClaimPayload } from '../../types/claim';
import { Card, CardContent } from '../ui/Card';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Button } from '../ui/Button';

const SECTION_TITLE = (n: string, label: string) => (
  <div className="flex items-center gap-3 mb-5 pb-4 border-b border-slate-100">
    <div className="w-6 h-6 rounded-full bg-emerald-600 text-white text-[11px] font-black flex items-center justify-center flex-shrink-0 shadow-sm">{n}</div>
    <h2 className="text-[13px] font-extrabold text-slate-800 uppercase tracking-wider">{label}</h2>
  </div>
);

export function ClaimForm() {
  const navigate = useNavigate();
  const [files, setFiles]     = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successClaimId, setSuccessClaimId] = useState('');
  const [error, setError]     = useState('');

  const [form, setForm] = useState<CreateClaimPayload>({
    patient_id: '', procedure_code: '', procedure: '',
    diagnosis_codes: [], service_date: '',
    provider_id: '', payer: 'Aetna', policy_id: '',
  });
  const [diagInput, setDiagInput] = useState('');

  const handleChange = (k: keyof CreateClaimPayload, v: string) =>
    setForm(prev => ({ ...prev, [k]: v }));

  const addDiag = () => {
    const code = diagInput.trim().toUpperCase();
    if (code && !form.diagnosis_codes.includes(code))
      setForm(prev => ({ ...prev, diagnosis_codes: [...prev.diagnosis_codes, code] }));
    setDiagInput('');
  };
  const removeDiag = (c: string) =>
    setForm(prev => ({ ...prev, diagnosis_codes: prev.diagnosis_codes.filter(x => x !== c) }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const claim = await createClaim(form);
      setSuccessClaimId(claim.claim_id);
      setShowSuccess(true);
      setLoading(false);
      setTimeout(() => navigate(`/hospital/claims/${claim.claim_id}`), 1800);
    } catch {
      setError('Failed to submit claim. Please try again.');
      setLoading(false);
    }
  };

  if (showSuccess) {
    return (
      <Card className="p-10 text-center flex flex-col items-center py-24 animate-fade-in-up border-emerald-100 shadow-xl">
        <div className="success-checkmark mb-6"><div className="check-icon"><span className="icon-line line-tip"/><span className="icon-line line-long"/><div className="icon-circle"/></div></div>
        <h2 className="text-xl font-black text-slate-900 mt-2">Claim Submitted Successfully!</h2>
        <p className="text-sm text-slate-500 mt-2">Claim ID: <span className="font-mono font-bold text-emerald-700 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-lg">{successClaimId}</span></p>
        <p className="text-xs text-slate-400 mt-2 animate-pulse font-medium">Redirecting to claim details…</p>
      </Card>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 animate-fade-in-up">
      {/* 1. Patient */}
      <Card>
        <CardContent className="p-6">
          {SECTION_TITLE('1', 'Patient Details')}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Input label="Patient ID" placeholder="e.g. PAT-001" value={form.patient_id} onChange={e => handleChange('patient_id', e.target.value)} />
            <Input label="Provider ID" placeholder="e.g. PRV-001" value={form.provider_id} onChange={e => handleChange('provider_id', e.target.value)} />
          </div>
        </CardContent>
      </Card>

      {/* 2. Claim Details */}
      <Card>
        <CardContent className="p-6">
          {SECTION_TITLE('2', 'Claim Details')}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Input label="Procedure" placeholder="e.g. Total Knee Replacement" value={form.procedure} onChange={e => handleChange('procedure', e.target.value)} />
            <Input label="Procedure Code" placeholder="e.g. 27447" value={form.procedure_code} onChange={e => handleChange('procedure_code', e.target.value)} />
            <Input type="date" label="Service Date" value={form.service_date} onChange={e => handleChange('service_date', e.target.value)} />
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Diagnosis Codes</label>
              <div className="flex gap-2">
                <Input placeholder="e.g. M17.11" value={diagInput} onChange={e => setDiagInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addDiag(); } }} />
                <Button type="button" variant="outline" onClick={addDiag} className="px-3 flex-shrink-0 text-emerald-700 border-emerald-200 bg-emerald-50 hover:bg-emerald-600 hover:text-white hover:border-emerald-600">
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              {form.diagnosis_codes.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {form.diagnosis_codes.map(c => (
                    <span key={c} className="inline-flex items-center gap-1.5 text-[10px] font-mono bg-emerald-50 text-emerald-800 px-2.5 py-1 rounded-lg border border-emerald-200 font-bold">
                      {c}
                      <button type="button" onClick={() => removeDiag(c)} className="text-emerald-400 hover:text-emerald-700 transition-colors"><X className="w-3 h-3" /></button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 3. Policy / Payer */}
      <Card>
        <CardContent className="p-6">
          {SECTION_TITLE('3', 'Policy / Payer')}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Select 
              label="Payer" 
              value={form.payer} 
              onChange={e => handleChange('payer', e.target.value)}
              options={[
                {label: 'Aetna', value: 'Aetna'},
                {label: 'CMS', value: 'cms'},
              ]}
            />
            <Input label="Policy ID" placeholder="e.g. CPB-0660" value={form.policy_id} onChange={e => handleChange('policy_id', e.target.value)} />
          </div>
        </CardContent>
      </Card>

      {/* 4. Documents */}
      <Card>
        <CardContent className="p-6">
          {SECTION_TITLE('4', 'Supporting Documents')}
          <p className="text-[12px] text-slate-500 mb-4 font-medium">Upload medical records, test results, and physician notes. Supported: PDF, JPG, PNG, DOCX.</p>
          <DocumentUploader onUpload={setFiles} />
          {files.length > 0 && (
            <div className="flex items-center gap-2 mt-3 text-[12px] font-bold text-emerald-700">
              <CheckCircle2 className="w-4 h-4" /> {files.length} file(s) attached
            </div>
          )}
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-[13px] px-4 py-3 rounded-xl font-semibold flex items-center gap-2 animate-fade-in-up">
          <X className="w-4 h-4" /> {error}
        </div>
      )}

      {/* Submit */}
      <div className="flex justify-end pt-2">
        <Button
          type="submit"
          isLoading={loading}
          className="min-w-[160px] text-[14px] font-extrabold shadow-md shadow-emerald-200 hover:shadow-lg hover:shadow-emerald-200"
        >
          Submit Claim →
        </Button>
      </div>
    </form>
  );
}

