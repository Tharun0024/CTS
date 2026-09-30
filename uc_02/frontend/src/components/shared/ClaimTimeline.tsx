import { Clock, CheckCircle2, XCircle, AlertTriangle, PlayCircle } from 'lucide-react';
import type { TimelineEvent } from '../../types/claim';
import { clsx } from 'clsx';

interface ClaimTimelineProps {
  events: TimelineEvent[];
  portal?: 'hospital' | 'insurance';
}

const CFG: Record<string, { icon: any; ring: string; dot: string; bg: string }> = {
  SUBMITTED:   { icon: PlayCircle,   ring: 'border-slate-300',   dot: 'bg-slate-400',   bg: 'bg-slate-50' },
  PROCESSING:  { icon: Clock,        ring: 'border-violet-300',  dot: 'bg-violet-500',  bg: 'bg-violet-50' },
  UNDER_REVIEW:{ icon: Clock,        ring: 'border-indigo-300',  dot: 'bg-indigo-500',  bg: 'bg-indigo-50' },
  MORE_INFO:   { icon: AlertTriangle,ring: 'border-amber-300',   dot: 'bg-amber-500',   bg: 'bg-amber-50' },
  ACCEPTED:    { icon: CheckCircle2, ring: 'border-emerald-300', dot: 'bg-emerald-500', bg: 'bg-emerald-50' },
  SUBMITTED_AGAIN: { icon: PlayCircle, ring: 'border-sky-300', dot: 'bg-sky-500', bg: 'bg-sky-50' },
  HUMAN_REVIEW: { icon: AlertTriangle, ring: 'border-blue-300', dot: 'bg-blue-500', bg: 'bg-blue-50' },
  REJECTED:    { icon: XCircle,      ring: 'border-red-300',     dot: 'bg-red-500',     bg: 'bg-red-50' },
};

export function ClaimTimeline({ events, portal = 'hospital' }: ClaimTimelineProps) {
  const sorted = [...events].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  const isHospital = portal === 'hospital';
  const accentBg   = isHospital ? 'bg-emerald-50' : 'bg-indigo-50';
  const accentIcon = isHospital ? 'text-emerald-600' : 'text-indigo-600';

  return (
    <div className="glass-panel rounded-2xl overflow-hidden animate-fade-in-up stagger-1 shadow-sm">
      <div className="flex items-center gap-2.5 px-5 py-3.5 border-b border-slate-100 bg-slate-50/60">
        <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center', accentBg)}>
          <Clock className={clsx('w-3.5 h-3.5', accentIcon)} />
        </div>
        <h3 className="text-[12px] font-extrabold text-slate-800 uppercase tracking-wider">Claim Timeline</h3>
      </div>

      <div className="p-5 space-y-4">
        {sorted.map((event, idx) => {
          const key = event.status ?? event.event;
          const cfg = CFG[key] || CFG.SUBMITTED;
          const Icon = cfg.icon;
          const isFirst = idx === 0;
          return (
            <div key={idx} className={clsx('flex items-start gap-3', `stagger-${(idx % 5) + 1} animate-fade-in-up`)}>
              <div className={clsx(
                'w-8 h-8 rounded-full border-2 flex items-center justify-center flex-shrink-0 shadow-sm',
                cfg.ring, cfg.bg,
                isFirst && 'shadow-md ring-2 ring-offset-2 ring-emerald-300'
              )}>
                <Icon className={clsx('w-3.5 h-3.5', isFirst ? accentIcon : 'text-slate-500')} />
              </div>
              <div className="flex-1 min-w-0 pt-1">
                <p className={clsx('text-[13px] leading-snug', isFirst ? 'font-extrabold text-slate-900' : 'font-semibold text-slate-700')}>
                  {event.message}
                </p>
                <p className="text-[10px] font-semibold text-slate-400 mt-0.5 uppercase tracking-wide">
                  {new Date(event.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
              {isFirst && (
                <span className="flex-shrink-0 text-[9px] font-black uppercase tracking-widest bg-emerald-100 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">Latest</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
