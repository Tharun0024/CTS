import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, ArrowRight, Lock, Mail } from 'lucide-react';

export function InsuranceLogin() {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);

  return (
    <div className="min-h-screen bg-slate-50 flex font-sans">
      {/* Left panel - branding/visual */}
      <div className="hidden lg:flex lg:w-1/2 bg-insurance-900 flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-insurance-900 opacity-90 z-0">
          <div className="absolute top-0 left-0 right-0 h-96 bg-gradient-to-b from-insurance-600/30 to-transparent"></div>
          {/* Decorative circles */}
          <div className="absolute -top-24 -left-24 w-96 h-96 bg-insurance-500 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
          <div className="absolute top-48 -right-24 w-96 h-96 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
        </div>
        
        <div className="relative z-10">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
            <div className="bg-white/10 p-2 rounded-lg backdrop-blur-md">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-white">AuthFlow <span className="text-insurance-300">Insurance</span></span>
          </div>
        </div>

        <div className="relative z-10 mb-20">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6 leading-tight">
            Intelligent policy assessment.
          </h1>
          <p className="text-insurance-100 text-lg max-w-md leading-relaxed">
            Automate triage, assess clinical evidence against policies instantly, and make decisions with confidence.
          </p>
        </div>
        
        <div className="relative z-10 text-insurance-200/60 text-sm">
          &copy; 2026 AuthFlow. All rights reserved.
        </div>
      </div>

      {/* Right panel - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-md bg-white p-8 rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
          
          <div className="lg:hidden flex items-center gap-2 mb-10 cursor-pointer" onClick={() => navigate('/')}>
            <div className="bg-insurance-600 p-2 rounded-lg">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-slate-900">AuthFlow</span>
          </div>

          <h2 className="text-2xl font-bold text-slate-900 mb-2">
            {isLogin ? 'Welcome back' : 'Create an account'}
          </h2>
          <p className="text-slate-500 mb-8">
            {isLogin ? 'Enter your details to access your queue.' : 'Start automating your triage today.'}
          </p>

          <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); navigate('/insurance/dashboard'); }}>
            {!isLogin && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700">Insurance Company</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <ShieldCheck className="h-5 w-5 text-slate-400" />
                  </div>
                  <input 
                    type="text" 
                    className="pl-10 w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-slate-900 focus:border-insurance-500 focus:ring-2 focus:ring-insurance-500/20 transition-all outline-none" 
                    placeholder="HealthShield Inc."
                  />
                </div>
              </div>
            )}
            
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Work Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-slate-400" />
                </div>
                <input 
                  type="email" 
                  className="pl-10 w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-slate-900 focus:border-insurance-500 focus:ring-2 focus:ring-insurance-500/20 transition-all outline-none" 
                  placeholder="you@insurance.com"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-slate-700">Password</label>
                {isLogin && <a href="#" className="text-sm font-medium text-insurance-600 hover:text-insurance-700">Forgot password?</a>}
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-slate-400" />
                </div>
                <input 
                  type="password" 
                  className="pl-10 w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-slate-900 focus:border-insurance-500 focus:ring-2 focus:ring-insurance-500/20 transition-all outline-none" 
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button 
              type="submit" 
              className="w-full bg-insurance-600 hover:bg-insurance-700 text-white font-medium py-2.5 rounded-xl transition-all shadow-sm shadow-insurance-200 mt-2 flex justify-center items-center gap-2 group"
            >
              {isLogin ? 'Sign in' : 'Create account'}
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </form>

          <div className="mt-8 text-center text-sm text-slate-500">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button 
              onClick={() => setIsLogin(!isLogin)} 
              className="font-medium text-insurance-600 hover:text-insurance-700"
            >
              {isLogin ? 'Sign up' : 'Log in'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
