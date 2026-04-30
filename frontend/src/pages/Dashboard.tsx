import { Link } from 'react-router-dom'
import { AlertTriangle, CheckCircle, Clock, TrendingUp, Zap, Shield, MapPin } from 'lucide-react'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'

// ── Demo telemetry: KCX-NYC-0042 thermal runaway vs KCX-CHI-0011 vibration bearing
const DEMO_TELEMETRY = Array.from({ length: 48 }, (_, i) => {
  const hour = i * 0.5
  // NYC-0042: pump seal degradation — temp rise, flow drop
  const degT = hour < 2 ? 0 : Math.min(1, (hour - 2) / 4)
  // CHI-0011: bearing fault — vibration climbs independently
  const degV = hour < 1 ? 0 : Math.min(1, (hour - 1) / 7)
  return {
    time: `${String(Math.floor(hour)).padStart(2, '0')}:${hour % 1 === 0 ? '00' : '30'}`,
    'NYC-0042 Temp': +(42 + degT * 45 + Math.random() * 0.5).toFixed(1),
    'NYC-0042 Flow': +(185 - degT * 65 + Math.random() * 2).toFixed(1),
    'CHI-0011 Vib': +(1.2 + degV * 8.5 + Math.random() * 0.06).toFixed(2),
  }
})

const RECENT_INCIDENTS = [
  { id: 'INC-2026-0847', device: 'KCX-NYC-0042', fault: 'KX-T2209-B', outcome: 'WORK_ORDER_DISPATCHED', severity: 'HIGH', ago: '38 min ago' },
  { id: 'INC-2026-0846', device: 'KCX-NYC-0044', fault: 'KX-V1103-A', outcome: 'WORK_ORDER_DISPATCHED', severity: 'MEDIUM', ago: '2h 17m ago' },
  { id: 'INC-2026-0845', device: 'KCX-NYC-0045', fault: 'KX-E4412-A', outcome: 'BLOCKED_BY_SAFETY', severity: 'HIGH', ago: '4h 24m ago' },
  { id: 'INC-2026-0843', device: 'KCX-CHI-0011', fault: 'KX-V1103-A', outcome: 'WORK_ORDER_DISPATCHED', severity: 'MEDIUM', ago: '19h ago' },
  { id: 'INC-2026-0836', device: 'KCX-NYC-0043', fault: null, outcome: 'NO_FAULT', severity: null, ago: '1d 18h ago' },
]

const FACILITIES = [
  { id: 'FAC-NYC-DC-01', city: 'New York', devices: 4, alerts: 3, faults: ['KX-T2209-B', 'KX-V1103-A', 'KX-E4412-A'] },
  { id: 'FAC-CHI-DC-02', city: 'Chicago', devices: 3, alerts: 1, faults: ['KX-V1103-A'] },
  { id: 'FAC-DFW-DC-03', city: 'Dallas', devices: 2, alerts: 2, faults: ['KX-E4412-A', 'KX-P3301-C'] },
  { id: 'FAC-LAX-DC-04', city: 'Los Angeles', devices: 2, alerts: 1, faults: ['KX-T2209-B'] },
  { id: 'FAC-SEA-DC-05', city: 'Seattle', devices: 1, alerts: 0, faults: [] },
]

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
          Autonomous Reliability Engineer — 12 devices · 5 facilities · real-time
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Active Incidents" value="7" subtitle="3 NYC · 2 DFW · 1 CHI · 1 LAX" icon={AlertTriangle} color="text-amber-400" />
        <StatCard title="Work Orders Today" value="5" subtitle="2 in progress · 3 dispatched" icon={CheckCircle} color="text-green-400" />
        <StatCard title="Avg Response Time" value="36s" subtitle="vs 45 min manual — 75× faster" icon={Clock} color="text-blue-400" />
        <StatCard title="Fleet F1 Score" value="0.93" subtitle="Baseline 0.91 · drift: none" icon={TrendingUp} color="text-purple-400" />
      </div>

      {/* Multi-device telemetry chart */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-white">Active Fault Comparison — Last 24h</h2>
            <p className="text-xs text-gray-400 mt-1">
              NYC-0042: thermal runaway (seal degradation, hour 2) · CHI-0011: bearing vibration escalation (hour 1)
            </p>
          </div>
          <div className="flex gap-2">
            <div className="flex items-center gap-2 text-xs bg-amber-900/40 text-amber-300 px-3 py-1.5 rounded-full border border-amber-700">
              <AlertTriangle className="h-3.5 w-3.5" /> KX-T2209-B
            </div>
            <div className="flex items-center gap-2 text-xs bg-purple-900/40 text-purple-300 px-3 py-1.5 rounded-full border border-purple-700">
              <AlertTriangle className="h-3.5 w-3.5" /> KX-V1103-A
            </div>
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
                <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="vibGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#6b7280' }} interval={7} />
            <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
              labelStyle={{ color: '#e5e7eb' }}
            />
            <Area type="monotone" dataKey="NYC-0042 Temp" stroke="#f59e0b" fill="url(#tempGrad)" name="NYC-0042 Temp (°C)" strokeWidth={2} />
            <Area type="monotone" dataKey="NYC-0042 Flow" stroke="#60a5fa" fill="url(#flowGrad)" name="NYC-0042 Flow (LPM)" strokeWidth={2} />
            <Area type="monotone" dataKey="CHI-0011 Vib" stroke="#a78bfa" fill="url(#vibGrad)" name="CHI-0011 Vibration (mm/s)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Facility overview + Agent pipeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <MapPin className="h-4 w-4 text-blue-400" /> Fleet — Facility Overview
          </h2>
          <div className="space-y-2">
            {FACILITIES.map(f => (
              <div key={f.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50">
                <div className="flex items-center gap-3">
                  <div className={`h-2.5 w-2.5 rounded-full ${f.alerts > 0 ? 'bg-amber-400' : 'bg-green-400'}`} />
                  <div>
                    <span className="text-sm font-medium text-gray-200">{f.city}</span>
                    <span className="text-xs text-gray-500 ml-2">{f.id}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <span className="text-gray-400">{f.devices} device{f.devices !== 1 ? 's' : ''}</span>
                  {f.alerts > 0 ? (
                    <div className="flex gap-1">
                      {f.faults.map(fc => (
                        <span key={fc} className="bg-amber-900/40 text-amber-300 border border-amber-700/50 px-2 py-0.5 rounded font-mono">
                          {fc}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-green-400 flex items-center gap-1">
                      <CheckCircle className="h-3 w-3" /> Nominal
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Zap className="h-4 w-4 text-blue-400" /> Agent Pipeline
          </h2>
          <div className="space-y-3">
            {[
              { name: 'Diagnostic Lead', version: 'v1.2', f1: '0.93' },
              { name: 'Technical Librarian', version: 'v1.1', f1: '0.95' },
              { name: 'Safety Auditor', version: 'v1.0', f1: '1.00' },
              { name: 'Orchestrator', version: 'v1.0', f1: '—' },
            ].map(agent => (
              <div key={agent.name} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-sm text-gray-200">{agent.name}</span>
                  <span className="text-xs text-gray-500">{agent.version}</span>
                </div>
                <div className="flex items-center gap-3">
                  {agent.f1 !== '—' && <span className="text-xs text-gray-400">F1: {agent.f1}</span>}
                  <Shield className="h-3.5 w-3.5 text-green-400" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent incidents */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-white">Recent Incidents</h2>
          <Link to="/incidents" className="text-xs text-blue-400 hover:text-blue-300">View all →</Link>
        </div>
        <div className="space-y-2">
          {RECENT_INCIDENTS.map(inc => (
            <Link key={inc.id} to={`/incidents/${inc.id}`} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50 hover:bg-gray-800 cursor-pointer transition-colors">
              <div className="flex items-center gap-3">
                <div className={`h-2 w-2 rounded-full ${
                  inc.outcome === 'BLOCKED_BY_SAFETY' ? 'bg-red-400' :
                  inc.outcome === 'NO_FAULT' ? 'bg-gray-500' : 'bg-green-400'
                }`} />
                <div>
                  <div className="text-sm font-medium text-gray-200">{inc.id}</div>
                  <div className="text-xs text-gray-500">{inc.device} · {inc.ago}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {inc.fault && (
                  <span className="text-xs bg-gray-700 px-2 py-0.5 rounded font-mono text-gray-300">{inc.fault}</span>
                )}
                {inc.severity && (
                  <span className={`text-xs font-medium ${inc.severity === 'HIGH' ? 'text-red-400' : 'text-amber-400'}`}>
                    {inc.severity}
                  </span>
                )}
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  inc.outcome === 'WORK_ORDER_DISPATCHED' ? 'bg-green-900/50 text-green-300' :
                  inc.outcome === 'NO_FAULT' ? 'bg-gray-700 text-gray-400' :
                  'bg-red-900/50 text-red-300'
                }`}>
                  {inc.outcome === 'WORK_ORDER_DISPATCHED' ? 'Dispatched' :
                   inc.outcome === 'NO_FAULT' ? 'No Fault' : 'Safety Block'}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
