import { mockCases } from '../../mock/cases';
import { StatusBadge } from '../../components/common/StatusBadge';
import { PriorityBadge } from '../../components/common/PriorityBadge';
import type { ClaimStatus } from '../../types/claim';
import { Shield, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';

export function InsuranceCaseDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const caseData = mockCases.find(c => c.authorization_id === id) || mockCases[1];

  return (
    <div className="max-w-7xl mx-auto w-full pb-10">
      <main className="flex-1 p-8 overflow-auto">
        {/* Header */}
        <div className="mb-8">
            <button onClick={() => navigate(-1)} className="text-sm font-medium text-slate-500 hover:text-slate-700 mb-4">&larr; Back to Queue</button>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{caseData.authorization_id}</h1>
                <p className="text-slate-500 mt-1">{caseData.request.procedure}</p>
              </div>
              <div className="flex items-center gap-3">
                <PriorityBadge priority={caseData.priority || 'MEDIUM'} />
                <StatusBadge status={(caseData.status as any) as ClaimStatus} className="text-sm px-4 py-1.5" />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Left Column: Data & Assessment */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* System Assessment */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden border-t-4 border-t-insurance-500">
                <div className="px-6 py-4 border-b border-slate-200 bg-insurance-50/30 flex items-center gap-2">
                  <Shield className="w-5 h-5 text-insurance-600" />
                  <h2 className="font-semibold text-slate-800">System Assessment: Policy Cross-Verification</h2>
                </div>
                
                <div className="p-6 space-y-6">
                  <div>
                    <p className="text-xs text-slate-500 font-medium mb-1">Policy Reference</p>
                    <p className="text-sm font-medium text-slate-900">Aetna CPB 0660 - Medical Necessity</p>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="p-4 border border-slate-200 rounded-lg bg-slate-50">
                      <p className="text-sm font-medium text-slate-700 mb-2">Required: Conservative treatment (12 weeks)</p>
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-slate-600">Patient Evidence: 14 weeks documented</p>
                        <span className="flex items-center text-green-600 text-sm font-medium"><CheckCircle2 className="w-4 h-4 mr-1"/> Satisfied</span>
                      </div>
                    </div>
                    
                    <div className="p-4 border border-red-100 rounded-lg bg-red-50/50">
                      <p className="text-sm font-medium text-slate-700 mb-2">Required: MRI evidence</p>
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-slate-600">Patient Evidence: Not provided</p>
                        <span className="flex items-center text-red-600 text-sm font-medium"><AlertTriangle className="w-4 h-4 mr-1"/> Missing</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Patient & Request Context */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h2 className="font-semibold text-slate-800 mb-4 pb-2 border-b border-slate-100">Context</h2>
                <div className="grid grid-cols-2 gap-8 text-sm">
                  <div>
                    <h3 className="font-medium text-slate-700 mb-2">Patient</h3>
                    <p className="text-slate-600">{caseData.patient.patient_id}</p>
                    <p className="text-slate-600">Age: {caseData.patient.age}</p>
                  </div>
                  <div>
                    <h3 className="font-medium text-slate-700 mb-2">Request</h3>
                    <p className="text-slate-600">{caseData.request.diagnosis}</p>
                    <p className="text-slate-600">{caseData.request.reason}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Review Action */}
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm sticky top-24">
                <div className="flex items-center gap-2 mb-4 border-b border-slate-100 pb-4">
                  <AlertCircle className="w-5 h-5 text-amber-500" />
                  <h2 className="font-semibold text-slate-800">Human Review</h2>
                </div>
                
                <div className="mb-6">
                  <p className="text-xs text-slate-500 font-medium mb-1">System Recommendation</p>
                  <p className="text-sm font-bold text-amber-600 bg-amber-50 inline-block px-2 py-1 rounded">MANUAL REVIEW</p>
                  <p className="text-sm text-slate-600 mt-2">Reason: Missing critical evidence required by policy.</p>
                </div>

                <div className="space-y-4 border-t border-slate-100 pt-6">
                  <label className="text-sm font-medium text-slate-700">Employee Decision</label>
                  
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer p-3 border border-slate-200 rounded-lg hover:bg-slate-50">
                      <input type="radio" name="decision" value="approve" className="text-insurance-600 focus:ring-insurance-500" />
                      <span className="text-sm font-medium text-slate-700">Approve</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer p-3 border border-slate-200 rounded-lg hover:bg-slate-50">
                      <input type="radio" name="decision" value="reject" className="text-insurance-600 focus:ring-insurance-500" />
                      <span className="text-sm font-medium text-slate-700">Reject</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer p-3 border border-insurance-200 bg-insurance-50/50 rounded-lg">
                      <input type="radio" name="decision" value="more_info" className="text-insurance-600 focus:ring-insurance-500" defaultChecked />
                      <span className="text-sm font-medium text-insurance-900">Request Information</span>
                    </label>
                  </div>

                  <div className="mt-4">
                    <label className="text-xs font-medium text-slate-700 mb-1 block">Comment</label>
                    <textarea 
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-insurance-500 focus:ring-1 focus:ring-insurance-500 outline-none resize-none" 
                      rows={3} 
                      placeholder="e.g. Please upload MRI results..."
                    ></textarea>
                  </div>

                  <button className="w-full bg-insurance-600 hover:bg-insurance-700 text-white font-medium py-2.5 rounded-xl transition-all shadow-sm shadow-insurance-200 mt-4">
                    Submit Decision
                  </button>
                </div>
              </div>
            </div>
          </div>
        </main>
    </div>
  );
}
