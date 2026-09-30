import { useNavigate } from 'react-router-dom';
import { Building2, ShieldCheck, ArrowRight, Activity, CheckCircle2 } from 'lucide-react';

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans selection:bg-brand-500 selection:text-white">
      {/* Navigation */}
      <nav className="w-full bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-brand-600 p-2 rounded-lg">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-slate-900">AuthFlow</span>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-20 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-100 via-slate-50 to-white">
        <div className="text-center max-w-3xl mb-16 animate-in fade-in slide-in-from-bottom-4 duration-1000">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 text-brand-600 font-medium text-sm mb-6 border border-brand-100">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500"></span>
            </span>
            Next-gen Authorization System
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold text-slate-900 tracking-tight mb-6 leading-tight">
            Seamless prior authorizations. <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-insurance-600">Zero friction.</span>
          </h1>
          <p className="text-xl text-slate-600 mb-10 max-w-2xl mx-auto leading-relaxed">
            Connect hospitals and insurance providers through our intelligent platform to process authorizations in minutes instead of days.
          </p>
        </div>

        {/* Portals Selection */}
        <div className="grid md:grid-cols-2 gap-8 w-full max-w-5xl">
          
          {/* Hospital Portal Card */}
          <div 
            onClick={() => navigate('/hospital/login')}
            className="group relative bg-white rounded-3xl p-8 border border-slate-200 shadow-sm hover:shadow-xl hover:border-brand-200 transition-all duration-300 cursor-pointer overflow-hidden transform hover:-translate-y-1"
          >
            <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity transform group-hover:scale-110 duration-500">
              <Building2 className="w-32 h-32 text-brand-600" />
            </div>
            
            <div className="relative z-10">
              <div className="w-14 h-14 bg-brand-50 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <Building2 className="w-7 h-7 text-brand-600" />
              </div>
              
              <h2 className="text-2xl font-bold text-slate-900 mb-3">Hospital Portal</h2>
              <p className="text-slate-600 mb-8 leading-relaxed min-h-[80px]">
                Submit authorization requests, upload medical documents, and track patient cases with our automated simulation tools.
              </p>
              
              <ul className="space-y-3 mb-8">
                {['Create manual authorizations', 'Simulate synthetic patient cases', 'Real-time case tracking'].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm text-slate-700">
                    <CheckCircle2 className="w-4 h-4 text-brand-500" />
                    {item}
                  </li>
                ))}
              </ul>
              
              <div className="flex items-center text-brand-600 font-semibold group-hover:text-brand-700">
                Access Hospital Portal 
                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </div>

          {/* Insurance Portal Card */}
          <div 
            onClick={() => navigate('/insurance/login')}
            className="group relative bg-white rounded-3xl p-8 border border-slate-200 shadow-sm hover:shadow-xl hover:border-insurance-200 transition-all duration-300 cursor-pointer overflow-hidden transform hover:-translate-y-1"
          >
            <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity transform group-hover:scale-110 duration-500">
              <ShieldCheck className="w-32 h-32 text-insurance-600" />
            </div>
            
            <div className="relative z-10">
              <div className="w-14 h-14 bg-insurance-50 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <ShieldCheck className="w-7 h-7 text-insurance-600" />
              </div>
              
              <h2 className="text-2xl font-bold text-slate-900 mb-3">Insurance Portal</h2>
              <p className="text-slate-600 mb-8 leading-relaxed min-h-[80px]">
                Review incoming cases, assess policies automatically, inspect clinical evidence, and process authorizations swiftly.
              </p>
              
              <ul className="space-y-3 mb-8">
                {['AI-assisted policy assessment', 'Manage triage queues', 'Request missing information'].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm text-slate-700">
                    <CheckCircle2 className="w-4 h-4 text-insurance-500" />
                    {item}
                  </li>
                ))}
              </ul>
              
              <div className="flex items-center text-insurance-600 font-semibold group-hover:text-insurance-700">
                Access Insurance Portal 
                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
