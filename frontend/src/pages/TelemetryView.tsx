import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const DEVICES = ['KCX-NYC-0042', 'KCX-NYC-0043', 'KCX-CHI-0011']

const makeTelemetry = (scenario: 'fault' | 'normal') =>
  Array.from({ length: 96 }, (_, i) => {
    const h = i * 0.25
    const d = scenario === 'fault' ? Math.max(0, Math.min(1, (h - 2) / 4)) : 0
    return {
      t: `${String(Math.floor(h)).padStart(2,'0')}:${h%1===0?'00':h%1===0.25?'15':h%1===0.5?'30':'45'}`,
      temp: +(42 + d * 45 + Math.random() * 0.4).toFixed(1),
      flow: +(185 - d * 65 + Math.random() * 1.5).toFixed(1),
      vibration: +(1.2 + d * 2.8 + Math.random() * 0.04).toFixed(2),
      voltage: +(480 + Math.random() * 4 - 2).toFixed(1),
    }
  })

const FAULT_DATA = makeTelemetry('fault')

export default function TelemetryView() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Live Telemetry</h1>
        <select className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-1.5">
          {DEVICES.map(d => <option key={d}>{d}</option>)}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {[
          { key: 'temp', label: 'Temperature (°C)', color: '#f59e0b', threshold: 75, yDomain: [30, 100] },
          { key: 'flow', label: 'Coolant Flow (LPM)', color: '#60a5fa', threshold: 150, yDomain: [80, 210] },
          { key: 'vibration', label: 'Vibration (mm/s)', color: '#a78bfa', threshold: 4.5, yDomain: [0, 6] },
          { key: 'voltage', label: 'Voltage (V)', color: '#34d399', threshold: 440, yDomain: [430, 510] },
        ].map(({ key, label, color, yDomain }) => (
          <div key={key} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-200">{label}</h3>
              <span className="text-xs text-gray-500">Last 24h — KCX-NYC-0042</span>
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={FAULT_DATA} margin={{ top: 5, right: 10, bottom: 0, left: -10 }}>
                <defs>
                  <linearGradient id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#6b7280' }} interval={23} />
                <YAxis domain={yDomain} tick={{ fontSize: 10, fill: '#6b7280' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 6, fontSize: 12 }}
                  labelStyle={{ color: '#e5e7eb' }}
                />
                <Area type="monotone" dataKey={key} stroke={color} fill={`url(#grad-${key})`} strokeWidth={1.5} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>
    </div>
  )
}
