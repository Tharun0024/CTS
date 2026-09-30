import { useState } from 'react';
import { PieChart, Download, Calendar, FileSpreadsheet, FileIcon, CheckCircle2, Loader2, BarChart3, Users, ShieldAlert, DollarSign } from 'lucide-react';
import { clsx } from 'clsx';
import { Card } from '../../components/ui/Card';


const reportTypes = [
  { id: 'financial', name: 'Financial Summary', desc: 'Revenue, collections, AR aging, write-offs', icon: DollarSign, gradient: 'from-emerald-500 to-teal-600' },
  { id: 'operational', name: 'Operational Metrics', desc: 'Claim volume, approval rates, TAT by payer', icon: BarChart3, gradient: 'from-blue-500 to-indigo-600' },
  { id: 'denials', name: 'Denials Analysis', desc: 'Denial reasons, codes, and appeal success rate', icon: ShieldAlert, gradient: 'from-rose-500 to-red-600' },
  { id: 'providers', name: 'Provider Performance', desc: 'Approval rates, volume, and revenue by physician', icon: Users, gradient: 'from-violet-500 to-purple-600' },
];

const dateRanges = [
  { id: 'today', label: 'Today' },
  { id: 'this-week', label: 'This Week' },
  { id: 'this-month', label: 'This Month' },
  { id: 'last-month', label: 'Last Month' },
  { id: 'ytd', label: 'Year to Date' },
  { id: 'custom', label: 'Custom Range' },
];

export function Reports() {
  const [reportType, setReportType] = useState('financial');
  const [dateRange, setDateRange] = useState('this-month');
  const [format, setFormat] = useState('pdf');
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);

  const handleGenerate = () => {
    setGenerating(true);
    setGenerated(false);
    setTimeout(() => {
      setGenerating(false);
      setGenerated(true);
      setTimeout(() => setGenerated(false), 4000);
    }, 1800);
  };

  const selectedType = reportTypes.find(r => r.id === reportType);

  return (
    <div className="max-w-4xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-md">
            <PieChart className="w-4 h-4 text-white" />
          </div>
          Reports & Analytics
        </h1>
        <p className="text-sm text-slate-500 font-medium mt-1">Generate and export custom operational and financial reports</p>
      </div>

      {/* Success Banner */}
      {generated && (
        <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-2xl animate-fade-in-up">
          <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div>
            <p className="text-sm font-bold text-emerald-900">Report generated successfully!</p>
            <p className="text-xs text-emerald-700 font-medium">Your {selectedType?.name} report is ready for download.</p>
          </div>
          <button className="ml-auto flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg transition-colors">
            <Download className="w-3.5 h-3.5" /> Download
          </button>
        </div>
      )}

      <Card className="p-6 sm:p-8 space-y-8">
        {/* Step 1: Report Type */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0">1</div>
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Select Report Type</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {reportTypes.map(type => {
              const isSelected = reportType === type.id;
              const Icon = type.icon;
              return (
                <button
                  key={type.id}
                  onClick={() => setReportType(type.id)}
                  className={clsx(
                    'text-left p-4 rounded-xl border-2 transition-all flex items-start gap-4 group',
                    isSelected ? 'border-transparent shadow-lg' : 'border-slate-100 bg-white hover:border-slate-200 hover:shadow-sm'
                  )}
                  style={isSelected ? { background: 'linear-gradient(135deg, #f0fdf4, #ecfdf5)' } : {}}
                >
                  <div className={clsx(
                    'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all',
                    isSelected ? `bg-gradient-to-br ${type.gradient} shadow-md` : 'bg-slate-100 group-hover:bg-slate-200'
                  )}>
                    <Icon className={clsx('w-5 h-5', isSelected ? 'text-white' : 'text-slate-500')} />
                  </div>
                  <div>
                    <h3 className={clsx('font-bold text-sm', isSelected ? 'text-slate-900' : 'text-slate-700')}>{type.name}</h3>
                    <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{type.desc}</p>
                  </div>
                  {isSelected && (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 ml-auto flex-shrink-0 mt-0.5" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Step 2: Date Range */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0">2</div>
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Date Range</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {dateRanges.map(range => (
              <button
                key={range.id}
                onClick={() => setDateRange(range.id)}
                className={clsx(
                  'px-4 py-2 rounded-xl text-sm font-semibold transition-all border',
                  dateRange === range.id
                    ? 'bg-slate-800 text-white border-slate-800 shadow-md'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 hover:border-slate-300'
                )}
              >
                {range.id === 'custom' && <Calendar className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />}
                {range.label}
              </button>
            ))}
          </div>
          {dateRange === 'custom' && (
            <div className="mt-4 flex items-center gap-4 animate-fade-in-up">
              <input type="date" className="bg-white border border-slate-200 rounded-xl text-sm px-3 py-2 focus:outline-none focus:border-emerald-500" style={{ colorScheme: 'light' }} />
              <span className="text-slate-400 font-bold text-sm">to</span>
              <input type="date" className="bg-white border border-slate-200 rounded-xl text-sm px-3 py-2 focus:outline-none focus:border-emerald-500" style={{ colorScheme: 'light' }} />
            </div>
          )}
        </div>

        {/* Step 3: Format */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0">3</div>
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Export Format</h2>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setFormat('pdf')}
              className={clsx(
                'flex-1 p-5 rounded-xl border-2 transition-all flex flex-col items-center gap-2',
                format === 'pdf'
                  ? 'border-rose-400 bg-rose-50 shadow-md'
                  : 'border-slate-100 bg-white hover:border-rose-200 hover:shadow-sm'
              )}
            >
              <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center', format === 'pdf' ? 'bg-rose-100' : 'bg-slate-100')}>
                <FileIcon className={clsx('w-5 h-5', format === 'pdf' ? 'text-rose-600' : 'text-slate-500')} />
              </div>
              <span className={clsx('font-bold text-sm', format === 'pdf' ? 'text-rose-700' : 'text-slate-600')}>PDF Document</span>
              <span className="text-xs text-slate-400">Best for sharing</span>
            </button>
            <button
              onClick={() => setFormat('csv')}
              className={clsx(
                'flex-1 p-5 rounded-xl border-2 transition-all flex flex-col items-center gap-2',
                format === 'csv'
                  ? 'border-emerald-400 bg-emerald-50 shadow-md'
                  : 'border-slate-100 bg-white hover:border-emerald-200 hover:shadow-sm'
              )}
            >
              <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center', format === 'csv' ? 'bg-emerald-100' : 'bg-slate-100')}>
                <FileSpreadsheet className={clsx('w-5 h-5', format === 'csv' ? 'text-emerald-600' : 'text-slate-500')} />
              </div>
              <span className={clsx('font-bold text-sm', format === 'csv' ? 'text-emerald-700' : 'text-slate-600')}>CSV / Excel</span>
              <span className="text-xs text-slate-400">Best for analysis</span>
            </button>
          </div>
        </div>

        {/* Submit */}
        <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-sm text-slate-500 font-medium">
            {selectedType && (
              <span>Generating: <span className="font-bold text-slate-800">{selectedType.name}</span> · {dateRanges.find(r => r.id === dateRange)?.label} · {format.toUpperCase()}</span>
            )}
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 px-7 py-3 bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-700 hover:to-teal-800 text-white text-sm font-bold rounded-xl transition-all shadow-lg shadow-emerald-200 hover:shadow-xl active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed min-w-[180px] justify-center"
          >
            {generating ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</>
            ) : (
              <><Download className="w-4 h-4" /> Generate Report</>
            )}
          </button>
        </div>
      </Card>
    </div>
  );
}
