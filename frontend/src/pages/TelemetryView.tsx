import { useState, useMemo } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { AlertTriangle, CheckCircle } from 'lucide-react'

// ── Fleet definition with per-device scenario and status ──────────────────────

const FLEET = [
  { id: 'KCX-NYC-0042', facility: 'FAC-NYC-DC-01', rack: 'RACK-B7-U12', scenario: 'thermal_runaway',    status: 'FAULT',   fault: 'KX-T2209-B' },
  { id: 'KCX-NYC-0043', facility: 'FAC-NYC-DC-01', rack: 'RACK-B7-U14', scenario: 'normal',             status: 'NOMINAL', fault: null },
  { id: 'KCX-NYC-0044', facility: 'FAC-NYC-DC-01', rack: 'RACK-C2-U01', scenario: 'vibration_bearing',  status: 'FAULT',   fault: 'KX-V1103-A' },
  { id: 'KCX-NYC-0045', facility: 'FAC-NYC-DC-01', rack: 'RACK-C2-U03', scenario: 'voltage_sag',        status: 'FAULT',   fault: 'KX-E4412-A' },
  { id: 'KCX-CHI-0011', facility: 'FAC-CHI-DC-02', rack: 'RACK-A3-U08', scenario: 'vibration_bearing',  status: 'FAULT',   fault: 'KX-V1103-A' },
  { id: 'KCX-CHI-0012', facility: 'FAC-CHI-DC-02', rack: 'RACK-A3-U10', scenario: 'sensor_fault',       status: 'WARN',    fault: 'KX-F2208-B' },
  { id: 'KCX-CHI-0013', facility: 'FAC-CHI-DC-02', rack: 'RACK-D1-U02', scenario: 'normal',             status: 'NOMINAL', fault: null },
  { id: 'KCX-DFW-0008', facility: 'FAC-DFW-DC-03', rack: 'RACK-F2-U05', scenario: 'voltage_sag',        status: 'FAULT',   fault: 'KX-E4412-A' },
  { id: 'KCX-DFW-0009', facility: 'FAC-DFW-DC-03', rack: 'RACK-F2-U07', scenario: 'pressure_drop',      status: 'FAULT',   fault: 'KX-P3301-C' },
  { id: 'KCX-LAX-0001', facility: 'FAC-LAX-DC-04', rack: 'RACK-A1-U04', scenario: 'normal',             status: 'NOMINAL', fault: null },
  { id: 'KCX-LAX-0002', facility: 'FAC-LAX-DC-04', rack: 'RACK-A1-U06', scenario: 'thermal_runaway',    status: 'FAULT',   fault: 'KX-T2209-B' },
  { id: 'KCX-SEA-0001', facility: 'FAC-SEA-DC-05', rack: 'RACK-B3-U01', scenario: 'normal',             status: 'NOMINAL', fault: null },
]

// ── Per-scenario telemetry generators ─────────────────────────────────────────
// Each produces 96 points (15-min intervals = 24h). Physics differs per fault type.

type Point = { t: string; temp: number; flow: number; vibration: number; voltage: number }

function r() { return Math.random() }

function makeThermalRunaway(): Point[] {
  return Array.from({ length: 96 }, (_, i) => {
    const h = i * 0.25
    const d = h < 2 ? 0 : Math.min(1, (h - 2) / 4)
    return {
      t: `${String(Math.floor(h)).padStart(2,'0')}:${['00','15','30','45'][i%4]}`,
      temp:     +(42 + d * 45 + r() * 0.5).toFixed(1),
      flow:     +(185 - d * 65 + r() * 2).toFixed(1),
      vibration:+(1.2 + d * 2.8 + r() * 0.05).toFixed(2),
      voltage:  +(480 + r() * 4 - 2).toFixed(1),
    }
  })
}

function makeVibrationBearing(): Point[] {
  return Array.from({ length: 96 }, (_, i) => {
    const h = i * 0.25
    const d = h < 1 ? 0 : Math.min(1, (h - 1) / 7)
    return {
      t: `${String(Math.floor(h)).padStart(2,'0')}:${['00','15','30','45'][i%4]}`,
      temp:     +(41.5 + d * 8 + r() * 0.4).toFixed(1),
      flow:     +(185 + r() * 2 - 1).toFixed(1),
      vibration:+(1.2 + d * 8.5 + h * 0.04 + r() * 0.08).toFixed(2),
      voltage:  +(480 + r() * 4 - 2).toFixed(1),
    }
  })
}

function makeVoltageSag(): Point[] {
  return Array.from({ length: 96 }, (_, i) => {
    const h = i * 0.25
    const d = h < 3 ? 0 : Math.min(1, (h - 3) / 2)
    return {
      t: `${String(Math.floor(h)).padStart(2,'0')}:${['00','15','30','45'][i%4]}`,
      temp:     +(478 - d * 478 * 0.18 + r() * 4 - 2).toFixed(1),  // mapped to voltage field
      flow:     +(185 + r() * 2 - 1).toFixed(1),
      vibration:+(1.2 + r() * 0.05).toFixed(2),
      voltage:  +(480 - d * 480 * 0.18 + r() * 3 - 1.5).toFixed(1),
    }
  })
}

function makePressureDrop(): Point[] {
  return Array.from({ length: 96 }, (_, i) => {
    const h = i * 0.25
    const d = h < 4 ? 0 : Math.min(1, (h - 4) / 5)
    return {
      t: `${String(Math.floor(h)).padStart(2,'0')}:${['00','15','30','45'][i%4]}`,
      temp:     +(42 + d * 9 + r() * 0.5).toFixed(1),
      flow:     +(185 - d * 55 + r() * 2).toFixed(1),  // flow drops, temp only slightly rises
      vibration:+(1.2 + r() * 0.05).toFixed(2),
      voltage:  +(480 + r() * 4 - 2).toFixed(1),
    }
  })
}

function makeSensorFault(): Point[] {
  return Array.from({ length: 96 }, (_, i) => {
    const h = i * 0.25
    const d = Math.min(1, h / 6)
    const erraticAmplitude = 1 + d * 14  // flow sensor gets noisier over time
    return {
      t: `${String(Math.floor(h)).padStart(2,'0')}:${['00','15','30','45'][i%4]}`,
      temp:     +(42 + r() * 0.5).toFixed(1),
      flow:     +(185 + (r() - 0.5) * 2 * erraticAmplitude).toFixed(1),
      vibration:+(1.2 + r() * 0.05).toFixed(2),
      voltage:  +(480 + r() * 4 - 2).toFixed(1),
    }
  })
}

function makeNormal(): Point[] {
  return Array.from({ length: 96 }, (_, i) => {
    const h = i * 0.25
    return {
      t: `${String(Math.floor(h)).padStart(2,'0')}:${['00','15','30','45'][i%4]}`,
      temp:     +(42 + r() * 0.6 - 0.3).toFixed(1),
      flow:     +(185 + r() * 3 - 1.5).toFixed(1),
      vibration:+(1.2 + r() * 0.06 - 0.03).toFixed(2),
      voltage:  +(480 + r() * 4 - 2).toFixed(1),
    }
  })
}

const GENERATORS: Record<string, () => Point[]> = {
  thermal_runaway: makeThermalRunaway,
  vibration_bearing: makeVibrationBearing,
  voltage_sag: makeVoltageSag,
  pressure_drop: makePressureDrop,
  sensor_fault: makeSensorFault,
  normal: makeNormal,
}

// ── Chart config varies by scenario ───────────────────────────────────────────

type ChartSpec = { key: keyof Point; label: string; color: string; threshold: number; yDomain: [number, number] }

const CHART_CONFIGS: Record<string, ChartSpec[]> = {
  default: [
    { key: 'temp',      label: 'Temperature (°C)', color: '#f59e0b', threshold: 75,  yDomain: [30, 110] },
    { key: 'flow',      label: 'Coolant Flow (LPM)', color: '#60a5fa', threshold: 150, yDomain: [80, 210] },
    { key: 'vibration', label: 'Vibration (mm/s)', color: '#a78bfa', threshold: 4.5, yDomain: [0, 10] },
    { key: 'voltage',   label: 'Voltage (V)', color: '#34d399', threshold: 440, yDomain: [380, 510] },
  ],
  voltage_sag: [
    { key: 'voltage',   label: 'Voltage (V)', color: '#34d399', threshold: 440, yDomain: [360, 510] },
    { key: 'flow',      label: 'Coolant Flow (LPM)', color: '#60a5fa', threshold: 150, yDomain: [80, 210] },
    { key: 'vibration', label: 'Vibration (mm/s)', color: '#a78bfa', threshold: 4.5, yDomain: [0, 4] },
    { key: 'temp',      label: 'Temperature (°C)', color: '#f59e0b', threshold: 75,  yDomain: [30, 60] },
  ],
  vibration_bearing: [
    { key: 'vibration', label: 'Vibration (mm/s)', color: '#a78bfa', threshold: 4.5, yDomain: [0, 12] },
    { key: 'temp',      label: 'Temperature (°C)', color: '#f59e0b', threshold: 75,  yDomain: [30, 60] },
    { key: 'flow',      label: 'Coolant Flow (LPM)', color: '#60a5fa', threshold: 150, yDomain: [80, 210] },
    { key: 'voltage',   label: 'Voltage (V)', color: '#34d399', threshold: 440, yDomain: [430, 510] },
  ],
}

const statusBadge = {
  FAULT:   'bg-red-900/50 text-red-300 border border-red-700',
  WARN:    'bg-amber-900/50 text-amber-300 border border-amber-700',
  NOMINAL: 'bg-green-900/50 text-green-300 border border-green-700',
}

const faultLabels: Record<string, string> = {
  thermal_runaway: 'Thermal Runaway — Seal Degradation',
  vibration_bearing: 'Bearing Micro-Failure — Vibration Escalation',
  voltage_sag: 'Supply Voltage Sag — Power Quality',
  pressure_drop: 'Strainer Blockage — Pressure Drop',
  sensor_fault: 'Flow Sensor Calibration Drift',
  normal: 'All sensors nominal',
}

export default function TelemetryView() {
  const [selectedId, setSelectedId] = useState('KCX-NYC-0042')

  const device = FLEET.find(d => d.id === selectedId) || FLEET[0]

  // Regenerate data when device changes (stable within a selection)
  const data = useMemo(() => GENERATORS[device.scenario](), [device.id])

  const charts = CHART_CONFIGS[device.scenario] || CHART_CONFIGS.default

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Telemetry</h1>
          <p className="text-xs text-gray-400 mt-1">{device.facility} · {device.rack} · 15-min intervals · last 24h</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedId}
            onChange={e => setSelectedId(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-1.5"
          >
            {FLEET.map(d => (
              <option key={d.id} value={d.id}>
                {d.id} ({d.status === 'NOMINAL' ? 'nominal' : d.fault ?? d.status})
              </option>
            ))}
          </select>
          <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full ${statusBadge[device.status as keyof typeof statusBadge]}`}>
            {device.status === 'NOMINAL'
              ? <><CheckCircle className="h-3.5 w-3.5" /> Nominal</>
              : <><AlertTriangle className="h-3.5 w-3.5" /> {device.fault}</>
            }
          </div>
        </div>
      </div>

      {/* Scenario description */}
      {device.status !== 'NOMINAL' && (
        <div className="bg-amber-900/20 border border-amber-700/50 rounded-xl px-4 py-3 flex items-center gap-3 text-sm">
          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
          <span className="text-amber-200">{faultLabels[device.scenario]}</span>
          {device.fault && <span className="text-xs font-mono bg-amber-900/50 px-2 py-0.5 rounded ml-auto">{device.fault}</span>}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {charts.map(({ key, label, color, yDomain }) => {
          const latest = data[data.length - 1][key] as number
          const isAlerting =
            (key === 'temp' && latest > 75) ||
            (key === 'flow' && latest < 150) ||
            (key === 'vibration' && latest > 4.5) ||
            (key === 'voltage' && latest < 440)

          return (
            <div key={key} className={`bg-gray-900 border rounded-xl p-5 ${isAlerting ? 'border-amber-700/60' : 'border-gray-800'}`}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-gray-200">{label}</h3>
                  {isAlerting && <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />}
                </div>
                <span className={`text-xs font-mono ${isAlerting ? 'text-amber-300' : 'text-gray-400'}`}>
                  Latest: {latest}
                </span>
              </div>
              <ResponsiveContainer width="100%" height={160}>
                <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 0, left: -10 }}>
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
          )
        })}
      </div>
    </div>
  )
}
