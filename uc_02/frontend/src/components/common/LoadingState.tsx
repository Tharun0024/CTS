import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  fullPage?: boolean;
}

export function LoadingState({ message = 'Loading...', fullPage = false }: LoadingStateProps) {
  if (fullPage) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-64">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
          <p className="text-sm font-medium text-slate-500">{message}</p>
        </div>
      </div>
    );
  }
  return (
    <div className="flex items-center justify-center py-12">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-6 h-6 text-brand-600 animate-spin" />
        <p className="text-sm text-slate-500">{message}</p>
      </div>
    </div>
  );
}
