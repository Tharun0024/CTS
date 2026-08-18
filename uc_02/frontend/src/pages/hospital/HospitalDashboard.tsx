import { useNavigate } from 'react-router-dom';
import { Plus, RefreshCcw, CheckCircle2, FileText, Clock, AlertTriangle, XCircle, Shield, Play, Square, RotateCcw, Activity, Users } from 'lucide-react';
import { useState, useEffect } from 'react';
import { getClaims } from '../../services/claimsApi';
import {
  startSimulationTrigger,
  getSimulationStatus,
  stopSimulation,
  resetSimulation,
  resimulateSimulation,
  listSimulations,
} from '../../services/simulationApi';
import type { SimulationStatus } from '../../services/simulationApi';
import type { Claim } from '../../types/claim';
import { Button } from '../../components/ui/Button';



export function HospitalDashboard() {
  const navigate = useNavigate();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [simStatus, setSimStatus] = useState<SimulationStatus | null>(null);
  const [simActionBusy, setSimActionBusy] = useState(false);
  const [allSims, setAllSims] = useState<any[]>([]);
  const [selectedResetId, setSelectedResetId] = useState<string>('');

  const fetchData = (showLoading = true) => {
    if (showLoading) setLoading(true);
    getSimulationStatus()
      .then(setSimStatus)
      .catch(() => setSimStatus(null));
    listSimulations()
      .then(setAllSims)
      .catch(() => {});
    getClaims().then(async (data) => {
      setClaims(data);
    }).finally(() => {
      if (showLoading) setLoading(false);
    });
  };

  useEffect(() => {
    fetchData(true);
    const timer = setInterval(() => {
      fetchData(false);
    }, 2000);
    return () => clearInterval(timer);
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      fetchData();
      setIsRefreshing(false);
      setLastUpdated(new Date());
    }, 800);
  };

  const handleStartSimulation = () => {
    const getErrorMessage = (error: unknown) => {
      if (typeof error === 'object' && error !== null && 'message' in error) {
        const message = (error as { message?: unknown }).message;
        if (typeof message === 'string' && message.trim().length > 0) {
          return message;
        }
      }
      return 'Failed to start simulation.';
    };

    setIsSimulating(true);
    startSimulationTrigger({ source: 'hospital-dashboard' })
      .then((response) => {
        fetchData();
        setLastUpdated(new Date());
        alert(response.message || 'Simulation trigger request sent.');
      })
      .catch((error: unknown) => {
        alert(getErrorMessage(error));
      })
      .finally(() => {
        setIsSimulating(false);
      });
  };

  const runSimAction = (action: () => Promise<unknown>) => {
    setSimActionBusy(true);
    action()
      .catch((error: unknown) => {
        alert((error as { message?: string })?.message ?? 'Simulation action failed.');
      })
      .finally(() => {
        setSimActionBusy(false);
        fetchData(false);
      });
  };
  const handleStopSimulation = () => runSimAction(() => stopSimulation());
  const handleResetSimulation = () => runSimAction(() => resetSimulation());
  const handleResetSelectedSimulation = () => {
    if (!selectedResetId) {
      alert('Please select a simulation run to reset.');
      return;
    }
    runSimAction(() => resetSimulation(selectedResetId));
    setSelectedResetId('');
  };
  const handleResimulate = () => {
    const simId = simStatus?.simulation_id;
    if (!simId) return;
    runSimAction(() => resimulateSimulation(simId));
  };

  const total = claims.length;
  const count = (s: string) => claims.filter(c => c.status === s).length;
  const accepted = count('ACCEPTED');
  const processing = claims.filter(c => ['PROCESSING', 'UNDER_REVIEW', 'SUBMITTED', 'SUBMITTED_AGAIN', 'RESUBMISSION_CHECK', 'DRAFT'].includes(c.status)).length;
  const needsInfo = count('MORE_INFO');
  const rejected = count('REJECTED');
  const humanReview = count('HUMAN_REVIEW');

  const pct = (num: number) => total > 0 ? Math.round((num / total) * 100) : 0;

  const kpis = [
    { label: 'Total Claims', value: total, sub: 'All time', icon: FileText, gradient: 'from-slate-700 to-slate-900', path: '/hospital/claims' },
    { label: 'Approved', value: accepted, sub: `${pct(accepted)}% approval rate`, icon: CheckCircle2, gradient: 'from-emerald-600 to-teal-700', path: '/hospital/claims' },
    { label: 'Processing', value: processing, sub: `${pct(processing)}% in pipeline`, icon: Clock, gradient: 'from-blue-600 to-indigo-700', path: '/hospital/claims' },
    { label: 'Needs Info', value: needsInfo, sub: needsInfo > 0 ? 'Action required' : 'All clear', icon: AlertTriangle, gradient: needsInfo > 0 ? 'from-amber-500 to-orange-600' : 'from-amber-400 to-amber-600', path: '/hospital/claims' },
    { label: 'Denied', value: rejected, sub: `${pct(rejected)}% rejection rate`, icon: XCircle, gradient: 'from-rose-600 to-red-700', path: '/hospital/claims' },
    { label: 'Human Review', value: humanReview, sub: `${pct(humanReview)}% hold`, icon: Users, gradient: 'from-indigo-600 to-indigo-850', path: '/hospital/claims' },
  ];

  // V1 Workflow stats
  const evidenceRequests = claims.filter(c => c.evidence_request_status === 'PENDING_PROVIDER_RESPONSE' || c.evidence_request_status === 'WAITING_FOR_PROVIDER').length;
  const evidenceAwaitingReview = claims.filter(c => c.evidence_request_status === 'RECEIVED' || c.evidence_request_status === 'UNDER_AGENT2_REVIEW').length;
  const releasedEvidence = claims.filter(c => c.agent2_result === 'RELEASED').length;
  const escalatedEvidence = claims.filter(c => c.agent2_result === 'ESCALATED_TO_HUMAN').length;
  const resubmissionsCount = claims.filter(c => c.resubmission_status === 'RESUBMITTED' || c.status === 'SUBMITTED_AGAIN').length;

  const workflowStats = [
    { label: 'Evidence Requests', value: evidenceRequests, desc: 'Awaiting provider response', icon: FileText, color: 'text-amber-600', bg: 'bg-amber-50' },
    { label: 'Awaiting Review', value: evidenceAwaitingReview, desc: 'Pending evaluation', icon: Clock, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Released Evidence', value: releasedEvidence, desc: 'Sent to payer', icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Escalated Evidence', value: escalatedEvidence, desc: 'Referred to human clinical', icon: AlertTriangle, color: 'text-rose-600', bg: 'bg-rose-50' },
    { label: 'Resubmissions', value: resubmissionsCount, desc: 'Re-evaluation in progress', icon: Shield, color: 'text-indigo-600', bg: 'bg-indigo-50' },
  ];



  // Mock data for charts
  return (
    <div className="max-w-7xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">

      {/* Hero Section */}
      <div className="relative rounded-2xl overflow-hidden p-6 sm:p-8 bg-gradient-to-r from-slate-900 to-slate-800 shadow-lg">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 opacity-10">
          <Shield className="w-full h-full text-white" />
        </div>
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="max-w-2xl">
            <div className="flex items-center gap-2 mb-3">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/10 text-emerald-300 text-[11px] font-bold border border-white/10">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live System
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mb-3">
              Hospital Operations Center
            </h1>
            <p className="text-slate-300 text-sm font-medium leading-relaxed">
              Real-time oversight of claims, authorizations, and revenue. Last refreshed {lastUpdated.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3 shrink-0">
            <Button
              variant="outline"
              onClick={handleRefresh}
              isLoading={isRefreshing}
              className="w-full sm:w-auto bg-white/10 hover:bg-white/20 text-white border-white/20"
            >
              <RefreshCcw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button
              variant="outline"
              onClick={handleStartSimulation}
              isLoading={isSimulating}
              className="w-full sm:w-auto bg-white/10 hover:bg-white/20 text-white border-white/20"
            >
              <Play className="w-4 h-4 mr-2" />
              Start Simulation
            </Button>
            <Button
              onClick={() => navigate('/hospital/claims/new')}
              className="w-full sm:w-auto bg-emerald-500 hover:bg-emerald-600 text-white border-none"
            >
              <Plus className="w-4 h-4 mr-2" strokeWidth={3} />
              New Claim
            </Button>
          </div>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        {kpis.map((kpi) => (
          <button
            key={kpi.label}
            onClick={() => navigate(kpi.path)}
            className={`group relative rounded-2xl p-5 text-left overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-xl bg-gradient-to-br ${kpi.gradient}`}
          >
            <div className="absolute inset-0 bg-white/0 group-hover:bg-white/10 transition-all rounded-2xl" />
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-white/15 backdrop-blur flex items-center justify-center border border-white/10 shadow-inner">
                <kpi.icon className="w-5 h-5 text-white" />
              </div>
            </div>
            <div className="mt-auto">
              {loading ? (
                <div className="space-y-2">
                  <div className="h-8 w-16 bg-white/20 animate-pulse rounded" />
                  <div className="h-3 w-20 bg-white/10 animate-pulse rounded" />
                </div>
              ) : (
                <>
                  <p className="text-3xl font-bold text-white tracking-tight leading-none mb-1">
                    {kpi.value.toLocaleString()}
                  </p>
                  <p className="text-xs font-semibold text-white/80 uppercase tracking-wide">{kpi.label}</p>
                  <p className="text-[11px] font-medium text-white/60 mt-1">{kpi.sub}</p>
                </>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* V1 Workflow & Evidence Metrics */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
        <div>
          <h2 className="text-xs font-black text-slate-700 uppercase tracking-widest flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-600" />
            Evidence & Resubmission Workflow (V1)
          </h2>
          <p className="text-[11px] text-slate-500 font-medium">Real-time status tracking of evidence loops and active resubmissions</p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {workflowStats.map((stat, i) => {
            const Icon = stat.icon;
            return (
              <div
                key={i}
                className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col justify-between hover:shadow-sm hover:border-emerald-200 transition-all group"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${stat.bg} group-hover:scale-105 transition-transform`}>
                    <Icon className={`w-4 h-4 ${stat.color}`} />
                  </div>
                  <span className="text-2xl font-black text-slate-800 tracking-tight">
                    {loading ? '...' : stat.value}
                  </span>
                </div>
                <div>
                  <p className="text-[11px] font-bold text-slate-700 leading-tight">{stat.label}</p>
                  <p className="text-[9px] font-medium text-slate-400 mt-0.5">{stat.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Simulation Control (V1 Simulation Manager — backend owns state) */}
      {simStatus && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xs font-black text-slate-700 uppercase tracking-widest flex items-center gap-2">
                <Activity className="w-4 h-4 text-blue-600" />
                Simulation Control
              </h2>
              <p className="text-[11px] text-slate-500 font-medium mt-0.5">
                Run {simStatus.simulation_id ?? '—'} · {String(simStatus.status ?? 'UNKNOWN').replace(/_/g, ' ')}
              </p>
            </div>
            <span className="text-[11px] font-extrabold bg-slate-100 text-slate-700 px-2.5 py-1 rounded-lg border border-slate-200">
              {simStatus.completed_count ?? (simStatus.patients?.filter(p => p.status === 'COMPLETED').length ?? 0)}/{simStatus.total_count ?? simStatus.patients?.length ?? 0} patients
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleStopSimulation}
              disabled={simActionBusy || !['RUNNING', 'STOPPING'].includes(simStatus.status ?? '')}
              className="text-red-600 border-red-200 hover:bg-red-50"
            >
              <Square className="w-3.5 h-3.5 mr-1.5" /> Stop
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleResimulate}
              disabled={simActionBusy || simStatus.status === 'RUNNING'}
            >
              <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Re-simulate
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleResetSimulation}
              disabled={simActionBusy}
              className="text-slate-600"
            >
              <Square className="w-3.5 h-3.5 mr-1.5" /> Reset All
            </Button>
          </div>
          {allSims.length > 0 && (
            <div className="flex items-center gap-2 pt-3 border-t border-slate-100 w-full flex-wrap">
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Target Reset Run:</label>
              <select
                value={selectedResetId}
                onChange={e => setSelectedResetId(e.target.value)}
                className="text-xs border border-slate-355 rounded px-2.5 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-brand-500 font-mono font-semibold"
              >
                <option value="">Select simulation run...</option>
                {allSims.map((sim: any) => (
                  <option key={sim.simulation_id} value={sim.simulation_id}>
                    {sim.simulation_id} ({sim.status})
                  </option>
                ))}
              </select>
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetSelectedSimulation}
                disabled={simActionBusy || !selectedResetId}
                className="text-red-750 border-red-200 hover:bg-red-50 bg-red-50/20"
              >
                Reset Selected Run
              </Button>
            </div>
          )}
        </div>
      )}



    </div>
  );
}
