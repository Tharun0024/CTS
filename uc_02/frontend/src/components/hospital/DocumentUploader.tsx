import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FileText, X, CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';

interface DocumentUploaderProps { onUpload: (files: File[]) => void; }

const fmt = (b: number) => b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(1)} MB`;

export function DocumentUploader({ onUpload }: DocumentUploaderProps) {
  const [files, setFiles] = useState<File[]>([]);

  const onDrop = useCallback((accepted: File[]) => {
    const merged = [...files, ...accepted.filter(f => !files.some(e => e.name === f.name))];
    setFiles(merged); onUpload(merged);
  }, [files, onUpload]);

  const remove = (name: string) => {
    const updated = files.filter(f => f.name !== name);
    setFiles(updated); onUpload(updated);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png','.jpg','.jpeg'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    multiple: true,
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200',
          isDragActive
            ? 'border-emerald-400 bg-emerald-50 shadow-inner'
            : 'border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/40 bg-slate-50/60'
        )}
      >
        <input {...getInputProps()} />
        <UploadCloud className={clsx('w-8 h-8 mx-auto mb-3 transition-colors', isDragActive ? 'text-emerald-600' : 'text-slate-400')} />
        <p className="text-[13px] font-bold text-slate-700">
          {isDragActive ? 'Drop files here…' : 'Drop files or click to browse'}
        </p>
        <p className="text-[11px] text-slate-400 font-medium mt-1">PDF, JPG, PNG, DOC, DOCX</p>
      </div>

      {files.length > 0 && (
        <ul className="space-y-2 animate-fade-in-up">
          {files.map(file => (
            <li key={file.name} className="flex items-center gap-3 p-3 bg-white border border-slate-100 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center flex-shrink-0">
                <FileText className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[12px] font-bold text-slate-800 truncate">{file.name}</p>
                <p className="text-[10px] font-medium text-slate-400">{fmt(file.size)}</p>
              </div>
              <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              <button
                type="button"
                onClick={() => remove(file.name)}
                className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
