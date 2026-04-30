import { AlertTriangle, CheckCircle, Clock, TrendingUp, Zap, Shield } from 'lucide-react'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'

const DEMO_TELEMETRY = Array.from({ length: 48 }, (_, i) => {
  const hour = i * 0.5
  const faultOnset = 2
  const degradation = hour < faultOnset ? 0 : Math.min(1, (hour - faultOnset) / 4)
  return {
    time: `${String(Math.floor(hour)).padStart(2, '0')}:${hour % 1 === 0 ? '00' : '30'}`,
    temperature: +(42 + degradation * 45 + Math.random() * 0.5).toFixed(1),
    coolantFlow: +(185 - degradation * 65 + Math.random() * 2).toFixed(1),
    vibration: +(1.2 + degradation * 2.8 + Math.random() * 0.05).toFixed(2),
  }
})

function StatCard({ title, value, subtitle, icon: Icon, color }: {
  title: string; value: string; subtitle: string
  icon: React.ElementType; color: string
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-400">{title}</span>
        <Icon className={`h-5 w-5 ${color}`} />
      </div>
      <div className={`text-3xl font-bold mb-1 ${color}`}>{value}</div>
      <div className="text-xs text-gray-500">{subtitle}</div>
    </div>
  )
}

export default function Dashboard() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Operations Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">
          Autonomous Reliability Engineer — real-time facility overview
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Active Incidents" value="1" subtitle="KCX-NYC-0042 — thermal" icon={AlertTriangle} color="text-amber-400" />
        <StatCard title="Work Orders Today" value="3" subtitle="2 resolved, 1 pending" icon={CheckCircle} color="text-green-400" />
        <StatCard title="Avg Response Time" value="38s" subtitle="vs 45 min manual" icon={Clock} color="text-blue-400" />
        <StatCard title="Agent F1 Score" value="0.91" subtitle="Baseline: 0.91 — no drift" icon={TrendingUp} color="text-purple-400" />
      </div>

      {/* Thermal Runaway Demo Chart */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-white">KCX-NYC-0042 — Thermal Event (Demo)</h2>
            <p className="text-xs text-gray-400 mt-1">
              Hidden fault: coolant pump seal degradation detected at hour 2 — 4h before threshold breach
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs bg-amber-900/40 text-amber-300 px-3 py-1.5 rounded-full border border-amber-700">
            <AlertTriangle className="h-3.5 w-3.5" />
            KX-T2209-B Active
          </div>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={DEMO_TELEMETRY} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <defs>
              <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="flowGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#6b7280' }} interval={7} />
            <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
              labelStyle={{ color: '#e5e7eb' }}
            />
            <Area type="monotone" dataKey="temperature" stroke="#f59e0b" fill="url(#tempGrad)" name="Temp (°C)" strokeWidth={2} />
            <Area type="monotone" dataKey="coolantFlow" stroke="#60a5fa" fill="url(#flowGrad)" name="Flow (LPM)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Agent Pipeline Status + Recent Incidents */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Zap className="h-4 w-4 text-blue-400" /> Agent Pipeline
          </h2>
          <div className="space-y-3">
            {[
              { name: 'Diagnostic Lead', version: 'v1.2', f1: '0.91', status: 'online' },
              { name: 'Technical Librarian', version: 'v1.1', f1: '0.93', status: 'online' },
              { name: 'Safety Auditor', version: 'v1.0', f1: '1.00', status: 'online' },
              { name: 'Orchestrator', version: 'v1.0', f1: '—', status: 'online' },
            ].map(agent => (
              <div key={agent.name} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-green-400" />
                  <span className="text-sm text-gray-200">{agent.name}</span>
                  <span className="text-xs text-gray-500">{agent.version}</span>
                </div>
                <div className="flex items-center gap-3">
                  {agent.f1 !== '—' && (
                    <span className="text-xs text-gray-400">F1: {agent.f1}</span>
                  )}
                  <Shield className="h-3.5 w-3.5 text-green-400" />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-white mb-4">Recent Incidents</h2>
          <div className="space-y-2">
            {[
              { id: 'INC-2025-0847', device: 'KCX-NYC-0042', fault: 'KX-T2209-B', outcome: 'WORK_ORDER_DISPATCHED', severity: 'HIGH', ago: '12 minutes ago' },
              { id: 'INC-2025-0831', device: 'KCX-CHI-0011', fault: 'KX-V1103-A', outcome: 'WORK_ORDER_DISPATCHED', severity: 'MEDIUM', ago: '3 hours ago' },
              { id: 'INC-2025-0819', device: 'KCX-NYC-0043', fault: null, outcome: 'NO_FAULT', severity: null, ago: '6 hours ago' },
            ].map(inc => (
              <div key={inc.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50 hover:bg-gray-800 cursor-pointer transition-colors">
                <div>
                  <div className="text-sm font-medium text-gray-200">{inc.id}</div>
                  <div className="text-xs text-gray-500">{inc.device} · {inc.ago}</div>
                </div>
                <div className="flex items-center gap-2">
                  {inc.fault && (
                    <span className="text-xs bg-gray-700 px-2 py-0.5 rounded text-gray-300">{inc.fault}</span>
                  )}
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    inc.outcome === 'WORK_ORDER_DISPATCHED' ? 'bg-green-900/50 text-green-300' :
                    inc.outcome === 'NO_FAULT' ? 'bg-gray-700 text-gray-400' :
                    'bg-red-900/50 text-red-300'
                  }`}>
                    {inc.outcome === 'WORK_ORDER_DISPATCHED' ? 'Dispatched' :
                     inc.outcome === 'NO_FAULT' ? 'No Fault' : 'Blocked'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
