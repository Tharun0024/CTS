import { useState } from 'react';
import { Loader2, Upload, CheckCircle2, X } from 'lucide-react';
import { DocumentUploader } from './DocumentUploader';
import { uploadDocuments } from '../../services/documentApi';
import { resubmitClaim } from '../../services/claimsApi';

interface MissingInfoUploaderProps {
  claimId: string; missingItems: string[];
  onSubmitted?: () => void;
  portal?: 'hospital' | 'insurance';
}

export function MissingInfoUploader({ claimId, missingItems, onSubmitted }: MissingInfoUploaderProps) {
  const [files, setFiles]     = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [done, setDone]       = useState(false);
  const [error, setError]     = useState('');

  const handleSubmit = async () => {
    if (!files.length) { setError('Please upload at least one document.'); return; }
    setError(''); setLoading(true);
    try {
      await uploadDocuments(claimId, files);
      await resubmitClaim(claimId);
      setDone(true); onSubmitted?.();
    } catch { setError('Upload failed. Please try again.'); }
    finally { setLoading(false); }
  };

  if (done) return (
    <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-5 py-4 flex items-center gap-3 shadow-sm animate-fade-in-up">
      <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
      <div>
        <p className="text-[13px] font-extrabold text-emerald-900">Documents submitted successfully</p>
        <p className="text-[11px] text-emerald-700 mt-0.5 font-medium">Your claim has been resubmitted for review.</p>
      </div>
    </div>
  );

  return (
    <div className="glass-panel rounded-2xl overflow-hidden shadow-sm animate-fade-in-up border-amber-100">
      <div className="px-5 py-3.5 border-b border-amber-100 bg-amber-50/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Upload className="w-4 h-4 text-amber-600" />
          <h3 className="text-[12px] font-extrabold text-amber-900 uppercase tracking-wider">Missing Information</h3>
        </div>
        <button
          type="button"
          onClick={() => alert('All missing information requested')}
          className="text-[10px] font-bold px-2.5 py-1 bg-white border border-amber-200 text-amber-700 hover:bg-amber-50 rounded-lg transition-colors"
        >
          Request All
        </button>
      </div>

      <div className="p-5 space-y-4">
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {missingItems.map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-[12px] font-semibold text-slate-700 bg-amber-50/60 border border-amber-100 px-3 py-2 rounded-lg">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0" />
              {item}
            </li>
          ))}
        </ul>

        <DocumentUploader onUpload={setFiles} />

        {error && (
          <div className="flex items-center gap-2 text-[12px] font-semibold text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-lg">
            <X className="w-4 h-4" /> {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading || files.length === 0}
          className="w-full inline-flex items-center justify-center gap-2 py-3 bg-emerald-600 hover:bg-emerald-700 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed text-white text-[13px] font-extrabold rounded-xl transition-all shadow-md shadow-emerald-100"
        >
          {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading &amp; Resubmitting…</> : <><Upload className="w-4 h-4" /> Submit &amp; Resubmit Claim</>}
        </button>
      </div>
    </div>
  );
}
