import { useState } from 'react';
import { BarChart3, TrendingUp, PieChart, LineChart, Activity, DollarSign, Clock, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar, PieChart as RechartsPieChart, Pie, Cell, Legend } from 'recharts';
import { clsx } from 'clsx';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/Card';

const mockTrendData = [
  { month: 'Jan', revenue: 4200, claims: 150 },
  { month: 'Feb', revenue: 4800, claims: 180 },
  { month: 'Mar', revenue: 5100, claims: 210 },
  { month: 'Apr', revenue: 4900, claims: 195 },
  { month: 'May', revenue: 5800, claims: 240 },
  { month: 'Jun', revenue: 6500, claims: 280 },
];

const mockPayerData = [
  { name: 'Aetna', value: 35, color: '#10b981' },
  { name: 'UHC', value: 25, color: '#3b82f6' },
  { name: 'Cigna', value: 20, color: '#8b5cf6' },
  { name: 'BCBS', value: 15, color: '#f59e0b' },
  { name: 'Other', value: 5, color: '#94a3b8' },
];

const mockDenialReasons = [
  { reason: 'Missing Info', count: 45 },
  { reason: 'Not Covered', count: 32 },
  { reason: 'Coding Error', count: 28 },
  { reason: 'Duplicate', count: 15 },
  { reason: 'Expired', count: 8 },
];

export function InsuranceAnalytics() {
  const [timeRange, setTimeRange] = useState('6m');

  const ranges = [
    { id: '1m', label: '1 Month' },
    { id: '3m', label: '3 Months' },
    { id: '6m', label: '6 Months' },
    { id: '1y', label: '1 Year' },
  ];

  return (
    <div className="max-w-7xl mx-auto w-full animate-fade-in-up space-y-6 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-md">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            Performance Analytics
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">Key metrics and trends for hospital operations</p>
        </div>
        <div className="flex bg-slate-100 p-1 rounded-xl">
          {ranges.map(r => (
            <button
              key={r.id}
              onClick={() => setTimeRange(r.id)}
              className={clsx(
                'px-4 py-1.5 text-xs font-bold rounded-lg transition-all',
                timeRange === r.id ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Top Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Revenue', value: '$24.5M', trend: '+12.5%', isUp: true, icon: DollarSign, gradient: 'from-emerald-500 to-teal-600' },
          { label: 'Approval Rate', value: '84.2%', trend: '+2.4%', isUp: true, icon: Activity, gradient: 'from-blue-500 to-indigo-600' },
          { label: 'Avg Turnaround', value: '4.2 Days', trend: '-1.1%', isUp: true, icon: Clock, gradient: 'from-violet-500 to-purple-600' },
          { label: 'Denial Rate', value: '15.8%', trend: '+0.5%', isUp: false, icon: TrendingUp, gradient: 'from-rose-500 to-red-600' },
        ].map(m => (
          <Card key={m.label} className="group hover:shadow-md transition-all hover:-translate-y-1">
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-4">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${m.gradient} flex items-center justify-center shadow-sm`}>
                  <m.icon className="w-5 h-5 text-white" />
                </div>
                <span className={clsx(
                  'flex items-center gap-1 text-[11px] font-black px-2 py-1 rounded-lg',
                  m.isUp ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'
                )}>
                  {m.isUp ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                  {m.trend}
                </span>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 group-hover:text-emerald-700 transition-colors tracking-tight">{m.value}</p>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-1">{m.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Trend */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LineChart className="w-5 h-5 text-emerald-500" /> Revenue vs Claims Volume
            </CardTitle>
            <CardDescription>Monthly trend over selected period</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={v => `$${v/1000}k`} />
                <RechartsTooltip
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(value: any) => [`$${value.toLocaleString()}`, 'Revenue']}
                />
                <Area type="monotone" dataKey="revenue" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#colorRev)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Payer Mix */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="w-5 h-5 text-indigo-500" /> Claims by Payer
            </CardTitle>
            <CardDescription>Distribution of submitted claims</CardDescription>
          </CardHeader>
          <CardContent className="h-72 flex items-center">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsPieChart>
                <Pie
                  data={mockPayerData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {mockPayerData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(value: any) => [`${value}%`, 'Share']}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', fontWeight: 600, color: '#475569' }} />
              </RechartsPieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Top Denials */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-rose-500" /> Top Denial Reasons
            </CardTitle>
            <CardDescription>Frequency of denial codes</CardDescription>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mockDenialReasons} layout="vertical" margin={{ top: 0, right: 30, left: 40, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                <YAxis dataKey="reason" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#475569', fontWeight: 600 }} />
                <RechartsTooltip
                  cursor={{ fill: '#f1f5f9' }}
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Bar dataKey="count" fill="#f43f5e" radius={[0, 6, 6, 0]} barSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

