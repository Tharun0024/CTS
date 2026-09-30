import { ClaimForm } from '../../components/hospital/ClaimForm';
import { FilePlus2, Phone, Lightbulb } from 'lucide-react';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';

export function CreateClaim() {
  return (
    <div className="max-w-6xl mx-auto w-full pb-10">
      <div className="mb-8 animate-fade-in-up">
        <div className="flex items-center gap-2 mb-1">
          <FilePlus2 className="w-6 h-6 text-emerald-600" />
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">New Authorization Claim</h1>
        </div>
        <p className="text-sm text-slate-500 font-medium">
          Fill in the form below with the claim details you want to submit.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <ClaimForm />
        </div>

        {/* Right-Side Help Panel */}
        <div className="space-y-6 lg:col-span-1 animate-fade-in-up stagger-1">
          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700 text-white">
            <CardContent className="p-6">
              <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center mb-4 border border-emerald-500/30">
                <Phone className="w-5 h-5 text-emerald-400" />
              </div>
              <h3 className="text-lg font-semibold mb-2 text-white">Need Help?</h3>
              <p className="text-slate-300 text-sm mb-6 leading-relaxed">
                Contact our support team for assistance with authorization claims.
              </p>
              <Button variant="secondary" className="w-full bg-white/10 hover:bg-white/20 text-white border-none shadow-none">
                Contact Support
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-5 h-5 text-amber-500" />
                <h3 className="font-semibold text-slate-900">Quick Tips</h3>
              </div>
              <ul className="space-y-3 text-sm text-slate-600">
                <li className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                  Add the most accurate procedure and diagnosis information available.
                </li>
                <li className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                  Double-check procedure and diagnosis codes.
                </li>
                <li className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                  Upload clear and legible documents.
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
