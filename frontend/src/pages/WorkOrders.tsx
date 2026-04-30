import { ClipboardList, Clock, CheckCircle, AlertCircle, Filter } from 'lucide-react'
import { useState } from 'react'

const ALL_WOS = [
  // Active / in-flight
  {
    id: 'WO-20260430-A9F2', incident: 'INC-2026-0847', device: 'KCX-NYC-0042', facility: 'FAC-NYC-DC-01',
    fault: 'KX-T2209-B', priority: 'HIGH', tech: 'Maria Santos', techId: 'TECH-001',
    status: 'IN_PROGRESS', parts: ['P-2209', 'P-3301'], eta: '~28 min remaining',
    description: 'Coolant Pump Seal Degradation — Thermal Escalation',
    created: '2026-04-30T14:32:38Z',
  },
  {
    id: 'WO-20260430-B3C1', incident: 'INC-2026-0846', device: 'KCX-NYC-0044', facility: 'FAC-NYC-DC-01',
    fault: 'KX-V1103-A', priority: 'MEDIUM', tech: 'David Petrov', techId: 'TECH-004',
    status: 'DISPATCHED', parts: ['P-1103-SKF', 'P-1103-SKF'], eta: '65 min est.',
    description: 'Pump Bearing Micro-Failure — Vibration Escalation',
    created: '2026-04-30T12:15:44Z',
  },
  {
    id: 'WO-20260429-C7D4', incident: 'INC-2026-0843', device: 'KCX-CHI-0011', facility: 'FAC-CHI-DC-02',
    fault: 'KX-V1103-A', priority: 'MEDIUM', tech: 'James Okafor', techId: 'TECH-002',
    status: 'IN_PROGRESS', parts: ['P-1103-SKF', 'P-1103-SKF'], eta: '~40 min remaining',
    description: 'Pump Bearing Micro-Failure — Vibration Escalation',
    created: '2026-04-29T18:44:41Z',
  },
  // Completed today
  {
    id: 'WO-20260429-E2A8', incident: 'INC-2026-0841', device: 'KCX-DFW-0009', facility: 'FAC-DFW-DC-03',
    fault: 'KX-P3301-C', priority: 'MEDIUM', tech: 'Aisha Mohammed', techId: 'TECH-005',
    status: 'COMPLETED', parts: ['P-STR-001'], eta: 'Done — 26 min',
    description: 'Coolant Pressure Drop — Strainer Blockage',
    created: '2026-04-29T11:22:27Z',
  },
  {
    id: 'WO-20260428-F4B9', incident: 'INC-2026-0839', device: 'KCX-LAX-0002', facility: 'FAC-LAX-DC-04',
    fault: 'KX-T2209-B', priority: 'HIGH', tech: 'Carlos Rivera', techId: 'TECH-006',
    status: 'COMPLETED', parts: ['P-2209', 'P-3301'], eta: 'Done — 44 min',
    description: 'Coolant Pump Seal Degradation — Thermal Escalation',
    created: '2026-04-28T22:05:39Z',
  },
  {
    id: 'WO-20260426-G1K3', incident: 'INC-2026-0829', device: 'KCX-CHI-0012', facility: 'FAC-CHI-DC-02',
    fault: 'KX-F2208-B', priority: 'LOW', tech: 'Lin Wei', techId: 'TECH-003',
    status: 'COMPLETED', parts: ['P-2208'], eta: 'Done — 21 min',
    description: 'Coolant Flow Sensor Fault — Calibration Drift',
    created: '2026-04-26T16:48:22Z',
  },
  {
    id: 'WO-20260423-H8J2', incident: 'INC-2026-0820', device: 'KCX-NYC-0042', facility: 'FAC-NYC-DC-01',
    fault: 'KX-T2209-B', priority: 'MEDIUM', tech: 'Maria Santos', techId: 'TECH-001',
    status: 'COMPLETED', parts: ['P-2209', 'P-3301'], eta: 'Done — 38 min',
    description: 'Coolant Pump Seal Degradation — Thermal Escalation',
    created: '2026-04-23T20:55:36Z',
  },
  {
    id: 'WO-20260422-J5L7', incident: 'INC-2026-0815', device: 'KCX-CHI-0013', facility: 'FAC-CHI-DC-02',
    fault: 'KX-V1103-A', priority: 'MEDIUM', tech: 'David Petrov', techId: 'TECH-004',
    status: 'COMPLETED', parts: ['P-1103-SKF', 'P-1103-SKF'], eta: 'Done — 62 min',
    description: 'Pump Bearing Micro-Failure — Vibration Escalation',
    created: '2026-04-22T13:40:43Z',
  },
  {
    id: 'WO-20260419-K2M4', incident: 'INC-2026-0807', device: 'KCX-NYC-0045', facility: 'FAC-NYC-DC-01',
    fault: 'KX-P3301-C', priority: 'LOW', tech: 'Lin Wei', techId: 'TECH-003',
    status: 'COMPLETED', parts: ['P-STR-001'], eta: 'Done — 24 min',
    description: 'Coolant Pressure Drop — Strainer Blockage',
    created: '2026-04-19T15:11:25Z',
  },
  {
    id: 'WO-20260416-L9N6', incident: 'INC-2026-0799', device: 'KCX-NYC-0043', facility: 'FAC-NYC-DC-01',
    fault: 'KX-C5501-A', priority: 'LOW', tech: 'James Okafor', techId: 'TECH-002',
    status: 'COMPLETED', parts: ['P-CB-5501'], eta: 'Done — 31 min',
    description: 'Control Board Communication Fault',
    created: '2026-04-16T09:45:33Z',
  },
  {
    id: 'WO-20260414-M3P8', incident: 'INC-2026-0793', device: 'KCX-CHI-0011', facility: 'FAC-CHI-DC-02',
    fault: 'KX-T2209-B', priority: 'HIGH', tech: 'Carlos Rivera', techId: 'TECH-006',
    status: 'COMPLETED', parts: ['P-2209', 'P-3301'], eta: 'Done — 41 min',
    description: 'Coolant Pump Seal Degradation — Thermal Escalation',
    created: '2026-04-14T18:22:40Z',
  },
  {
    id: 'WO-20260412-N7Q1', incident: 'INC-2026-0788', device: 'KCX-DFW-0009', facility: 'FAC-DFW-DC-03',
    fault: 'KX-P3301-C', priority: 'MEDIUM', tech: 'Aisha Mohammed', techId: 'TECH-005',
    status: 'COMPLETED', parts: ['P-STR-001'], eta: 'Done — 27 min',
    description: 'Coolant Pressure Drop — Strainer Blockage',
    created: '2026-04-12T14:05:28Z',
  },
]

const statusConfig = {
  IN_PROGRESS: { label: 'In Progress', color: 'bg-blue-900/30 text-blue-300 border-blue-700', icon: Clock },
  DISPATCHED:  { label: 'Dispatched',  color: 'bg-amber-900/30 text-amber-300 border-amber-700', icon: AlertCircle },
  COMPLETED:   { label: 'Completed',   color: 'bg-green-900/30 text-green-300 border-green-700', icon: CheckCircle },
  CANCELLED:   { label: 'Cancelled',   color: 'bg-gray-700 text-gray-400 border-gray-600', icon: Clock },
}

const priorityColor = {
  HIGH: 'bg-red-900/50 text-red-300 border-red-700',
  MEDIUM: 'bg-amber-900/50 text-amber-300 border-amber-700',
  LOW: 'bg-blue-900/50 text-blue-300 border-blue-700',
  CRITICAL: 'bg-red-700 text-white border-red-600',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const STATUS_FILTERS = ['All', 'IN_PROGRESS', 'DISPATCHED', 'COMPLETED']

export default function WorkOrders() {
  const [statusFilter, setStatusFilter] = useState('All')

  const workOrders = ALL_WOS.filter(wo => statusFilter === 'All' || wo.status === statusFilter)

  const active = ALL_WOS.filter(w => w.status === 'IN_PROGRESS' || w.status === 'DISPATCHED').length
  const completed = ALL_WOS.filter(w => w.status === 'COMPLETED').length

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Work Orders</h1>
          <p className="text-gray-400 text-sm mt-1">
            {ALL_WOS.length} total · {active} active · {completed} completed · 6 technicians
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <Filter className="h-4 w-4 text-gray-500" />
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-1.5"
          >
            {STATUS_FILTERS.map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div className="space-y-3">
        {workOrders.map(wo => {
          const { label, color, icon: StatusIcon } = statusConfig[wo.status as keyof typeof statusConfig] || statusConfig.DISPATCHED
          return (
            <div key={wo.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 flex-wrap">
                    <ClipboardList className="h-4 w-4 text-blue-400 shrink-0" />
                    <span className="font-mono font-semibold text-white text-sm">{wo.id}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${priorityColor[wo.priority as keyof typeof priorityColor]}`}>
                      {wo.priority}
                    </span>
                    <span className="font-mono text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">{wo.fault}</span>
                  </div>
                  <div className="text-sm text-gray-400 mt-1.5 ml-7">{wo.description}</div>
                  <div className="text-xs text-gray-600 mt-0.5 ml-7">{wo.device} · {wo.facility} · Incident {wo.incident}</div>
                </div>
                <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border whitespace-nowrap ${color}`}>
                  <StatusIcon className="h-3.5 w-3.5" />
                  {label}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm ml-7">
                <div>
                  <div className="text-xs text-gray-500 mb-1">Assigned To</div>
                  <div className="text-gray-200">{wo.tech}</div>
                  <div className="text-xs text-gray-600">{wo.techId}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">Parts Required</div>
                  <div className="flex gap-1 flex-wrap">
                    {wo.parts.map((p, i) => (
                      <span key={`${p}-${i}`} className="text-xs font-mono bg-gray-800 text-gray-300 px-2 py-0.5 rounded">{p}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">ETA / Resolution</div>
                  <div className={`text-sm ${wo.eta.startsWith('Done') ? 'text-green-400' : 'text-gray-200'}`}>{wo.eta}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">Created</div>
                  <div className="text-xs text-gray-400">{formatDate(wo.created)}</div>
                </div>
              </div>
            </div>
          )
        })}
        {workOrders.length === 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center text-gray-500 text-sm">
            No work orders match the selected status filter.
          </div>
        )}
      </div>
    </div>
  )
}
