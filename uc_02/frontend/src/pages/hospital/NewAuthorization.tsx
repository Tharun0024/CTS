import { useState } from 'react';
import { DocumentUploader } from '../../components/hospital/DocumentUploader';
import { Activity, Building2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function NewAuthorization() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'simulate' | 'manual'>('manual');
  
  const handleUpload = (files: File[]) => {
    console.log("Uploaded files:", files);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="w-full bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/hospital/dashboard')}>
            <div className="bg-brand-600 p-2 rounded-lg">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-slate-900">Hospital Portal</span>
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">New Authorization</h1>
          <p className="text-slate-600">Create a new prior authorization request manually or via simulation.</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden mb-8">
          <div className="flex border-b border-slate-200">
            <button 
              className={`flex-1 py-4 font-medium text-sm transition-colors ${activeTab === 'simulate' ? 'text-brand-600 border-b-2 border-brand-600 bg-brand-50/30' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'}`}
              onClick={() => setActiveTab('simulate')}
            >
              SIMULATE PATIENT
            </button>
            <button 
              className={`flex-1 py-4 font-medium text-sm transition-colors ${activeTab === 'manual' ? 'text-brand-600 border-b-2 border-brand-600 bg-brand-50/30' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'}`}
              onClick={() => setActiveTab('manual')}
            >
              MANUAL REQUEST
            </button>
          </div>
          
          <div className="p-8">
            {activeTab === 'simulate' && (
              <div className="flex flex-col items-center justify-center py-12 text-center animate-in fade-in">
                <Activity className="w-16 h-16 text-brand-200 mb-6" />
                <h3 className="text-xl font-semibold text-slate-900 mb-2">Generate synthetic case</h3>
                <p className="text-slate-500 max-w-md mb-8">Use our Synthea integration to generate a realistic patient case and automatically submit an authorization request.</p>
                <button className="bg-brand-600 hover:bg-brand-700 text-white font-medium py-3 px-8 rounded-xl transition-all shadow-sm shadow-brand-200">
                  Generate Case
                </button>
              </div>
            )}

            {activeTab === 'manual' && (
              <form className="space-y-10 animate-in fade-in" onSubmit={(e) => e.preventDefault()}>
                
                {/* Patient Details */}
                <section>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-100">1. Patient Details</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Patient ID</label>
                      <input type="text" className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none" placeholder="e.g. SYN-001" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Patient Name</label>
                      <input type="text" className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none" placeholder="John Doe" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Date of Birth</label>
                      <input type="date" className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Age</label>
                      <input type="number" className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none" placeholder="57" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Gender</label>
                      <select className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none bg-white">
                        <option>Select Gender</option>
                        <option>Male</option>
                        <option>Female</option>
                        <option>Other</option>
                      </select>
                    </div>
                  </div>
                </section>

                {/* Insurance Details */}
                <section>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-100">2. Insurance Details</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Provider</label>
                      <input type="text" value="Demo Payer" disabled className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-slate-500" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Member ID</label>
                      <input type="text" className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none" placeholder="SYN-INS-001" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Plan</label>
                      <select className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none bg-white">
                        <option>Gold</option>
                        <option>Silver</option>
                        <option>Bronze</option>
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Policy ID</label>
                      <input type="text" className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none" placeholder="CPB-0660" />
                    </div>
                  </div>
                </section>

                {/* Clinical Information */}
                <section>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-100">3. Clinical Information</h3>
                  <div className="grid grid-cols-1 gap-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700">Diagnosis</label>
                        <input type="text" className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none" placeholder="Osteoarthritis" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700">Procedure</label>
                        <input type="text" className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none" placeholder="Knee Replacement" />
                      </div>
                    </div>
                    
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Reason</label>
                      <textarea rows={2} className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none resize-none" placeholder="Severe pain and functional limitation" />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700">Previous Treatment</label>
                        <textarea rows={2} className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none resize-none" placeholder="Physical therapy for 14 weeks" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700">Clinical Findings</label>
                        <textarea rows={2} className="w-full rounded-lg border border-slate-300 px-4 py-2 text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none resize-none" placeholder="Reduced mobility" />
                      </div>
                    </div>
                  </div>
                </section>

                {/* Evidence Upload */}
                <section>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-100">4. Document Upload</h3>
                  <p className="text-sm text-slate-500 mb-4">Please provide all necessary medical records, test results, and physician notes to support this request.</p>
                  <DocumentUploader onUpload={handleUpload} />
                </section>
                
                <div className="pt-6 border-t border-slate-200 flex justify-end">
                  <button type="submit" className="bg-brand-600 hover:bg-brand-700 text-white font-medium py-3 px-8 rounded-xl transition-all shadow-sm shadow-brand-200">
                    Submit Authorization
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
