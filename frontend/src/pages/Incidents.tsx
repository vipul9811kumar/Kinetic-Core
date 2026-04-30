import { Link } from 'react-router-dom'
import { AlertTriangle, CheckCircle, XCircle, ChevronRight, Filter } from 'lucide-react'
import { useState } from 'react'

const ALL_INCIDENTS = [
  // Today (2026-04-30)
  { id: 'INC-2026-0847', device: 'KCX-NYC-0042', facility: 'NYC', fault: 'KX-T2209-B', severity: 'HIGH',   outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-30T14:32:00Z', elapsed: '38s' },
  { id: 'INC-2026-0846', device: 'KCX-NYC-0044', facility: 'NYC', fault: 'KX-V1103-A', severity: 'MEDIUM', outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-30T12:15:00Z', elapsed: '44s' },
  { id: 'INC-2026-0845', device: 'KCX-NYC-0045', facility: 'NYC', fault: 'KX-E4412-A', severity: 'HIGH',   outcome: 'BLOCKED_BY_SAFETY',    started: '2026-04-30T10:08:00Z', elapsed: '31s' },
  // Yesterday (2026-04-29)
  { id: 'INC-2026-0843', device: 'KCX-CHI-0011', facility: 'CHI', fault: 'KX-V1103-A', severity: 'MEDIUM', outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-29T18:44:00Z', elapsed: '41s' },
  { id: 'INC-2026-0841', device: 'KCX-DFW-0009', facility: 'DFW', fault: 'KX-P3301-C', severity: 'MEDIUM', outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-29T11:22:00Z', elapsed: '27s' },
  // 2 days ago (2026-04-28)
  { id: 'INC-2026-0839', device: 'KCX-LAX-0002', facility: 'LAX', fault: 'KX-T2209-B', severity: 'HIGH',   outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-28T22:05:00Z', elapsed: '39s' },
  { id: 'INC-2026-0836', device: 'KCX-NYC-0043', facility: 'NYC', fault: null,          severity: null,     outcome: 'NO_FAULT',             started: '2026-04-28T14:17:00Z', elapsed: '5s'  },
  // 3 days ago
  { id: 'INC-2026-0833', device: 'KCX-DFW-0008', facility: 'DFW', fault: 'KX-E4412-A', severity: 'HIGH',   outcome: 'BLOCKED_BY_SAFETY',    started: '2026-04-27T09:33:00Z', elapsed: '29s' },
  // 4 days ago
  { id: 'INC-2026-0829', device: 'KCX-CHI-0012', facility: 'CHI', fault: 'KX-F2208-B', severity: 'LOW',    outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-26T16:48:00Z', elapsed: '22s' },
  // 5 days ago
  { id: 'INC-2026-0825', device: 'KCX-SEA-0001', facility: 'SEA', fault: null,          severity: null,     outcome: 'NO_FAULT',             started: '2026-04-25T08:12:00Z', elapsed: '4s'  },
  // 7 days ago
  { id: 'INC-2026-0820', device: 'KCX-NYC-0042', facility: 'NYC', fault: 'KX-T2209-B', severity: 'MEDIUM', outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-23T20:55:00Z', elapsed: '36s' },
  // 8 days ago
  { id: 'INC-2026-0815', device: 'KCX-CHI-0013', facility: 'CHI', fault: 'KX-V1103-A', severity: 'MEDIUM', outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-22T13:40:00Z', elapsed: '43s' },
  // 9 days ago
  { id: 'INC-2026-0811', device: 'KCX-LAX-0001', facility: 'LAX', fault: null,          severity: null,     outcome: 'NO_FAULT',             started: '2026-04-21T07:28:00Z', elapsed: '4s'  },
  // 11 days ago
  { id: 'INC-2026-0807', device: 'KCX-NYC-0045', facility: 'NYC', fault: 'KX-P3301-C', severity: 'LOW',    outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-19T15:11:00Z', elapsed: '25s' },
  // 12 days ago
  { id: 'INC-2026-0803', device: 'KCX-DFW-0008', facility: 'DFW', fault: 'KX-E4412-A', severity: 'HIGH',   outcome: 'BLOCKED_BY_SAFETY',    started: '2026-04-18T11:02:00Z', elapsed: '30s' },
  // 14 days ago
  { id: 'INC-2026-0799', device: 'KCX-NYC-0043', facility: 'NYC', fault: 'KX-C5501-A', severity: 'LOW',    outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-16T09:45:00Z', elapsed: '33s' },
  // 16 days ago
  { id: 'INC-2026-0793', device: 'KCX-CHI-0011', facility: 'CHI', fault: 'KX-T2209-B', severity: 'HIGH',   outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-14T18:22:00Z', elapsed: '40s' },
  // 18 days ago
  { id: 'INC-2026-0788', device: 'KCX-DFW-0009', facility: 'DFW', fault: 'KX-P3301-C', severity: 'MEDIUM', outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-12T14:05:00Z', elapsed: '28s' },
  // 20 days ago
  { id: 'INC-2026-0781', device: 'KCX-LAX-0002', facility: 'LAX', fault: 'KX-V1103-A', severity: 'MEDIUM', outcome: 'WORK_ORDER_DISPATCHED', started: '2026-04-10T10:35:00Z', elapsed: '45s' },
  // 22 days ago
  { id: 'INC-2026-0774', device: 'KCX-SEA-0001', facility: 'SEA', fault: 'KX-E4412-A', severity: 'HIGH',   outcome: 'BLOCKED_BY_SAFETY',    started: '2026-04-08T07:18:00Z', elapsed: '31s' },
]

const outcomeIcon: Record<string, React.ElementType> = {
  WORK_ORDER_DISPATCHED: CheckCircle,
  NO_FAULT: CheckCircle,
  BLOCKED_BY_SAFETY: XCircle,
  IN_PROGRESS: AlertTriangle,
}

const outcomeColors: Record<string, string> = {
  WORK_ORDER_DISPATCHED: 'text-green-400',
  NO_FAULT: 'text-gray-400',
  BLOCKED_BY_SAFETY: 'text-red-400',
  IN_PROGRESS: 'text-amber-400',
}

const severityColor: Record<string, string> = {
  HIGH: 'text-red-400',
  MEDIUM: 'text-amber-400',
  LOW: 'text-blue-400',
  CRITICAL: 'text-red-500',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const FACILITIES = ['All', 'NYC', 'CHI', 'DFW', 'LAX', 'SEA']
const OUTCOMES = ['All', 'WORK_ORDER_DISPATCHED', 'BLOCKED_BY_SAFETY', 'NO_FAULT']

export default function Incidents() {
  const [facilityFilter, setFacilityFilter] = useState('All')
  const [outcomeFilter, setOutcomeFilter] = useState('All')

  const incidents = ALL_INCIDENTS.filter(inc =>
    (facilityFilter === 'All' || inc.facility === facilityFilter) &&
    (outcomeFilter === 'All' || inc.outcome === outcomeFilter)
  )

  const stats = {
    total: ALL_INCIDENTS.length,
    dispatched: ALL_INCIDENTS.filter(i => i.outcome === 'WORK_ORDER_DISPATCHED').length,
    blocked: ALL_INCIDENTS.filter(i => i.outcome === 'BLOCKED_BY_SAFETY').length,
    noFault: ALL_INCIDENTS.filter(i => i.outcome === 'NO_FAULT').length,
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Incidents</h1>
          <p className="text-gray-400 text-sm mt-1">Last 30 days · {stats.total} total · {stats.dispatched} dispatched · {stats.blocked} safety blocks · {stats.noFault} no-fault</p>
        </div>
        <div className="flex gap-2 items-center">
          <Filter className="h-4 w-4 text-gray-500" />
          <select
            value={facilityFilter}
            onChange={e => setFacilityFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-1.5"
          >
            {FACILITIES.map(f => <option key={f}>{f}</option>)}
          </select>
          <select
            value={outcomeFilter}
            onChange={e => setOutcomeFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-1.5"
          >
            {OUTCOMES.map(o => <option key={o}>{o}</option>)}
          </select>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wide">
              <th className="px-5 py-3 text-left">Incident ID</th>
              <th className="px-5 py-3 text-left">Device</th>
              <th className="px-5 py-3 text-left">Fault Code</th>
              <th className="px-5 py-3 text-left">Severity</th>
              <th className="px-5 py-3 text-left">Outcome</th>
              <th className="px-5 py-3 text-left">Started</th>
              <th className="px-5 py-3 text-left">Response</th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {incidents.map(inc => {
              const OutcomeIcon = outcomeIcon[inc.outcome] || AlertTriangle
              return (
                <tr key={inc.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                  <td className="px-5 py-3 font-mono text-gray-200 text-xs">{inc.id}</td>
                  <td className="px-5 py-3">
                    <div className="text-gray-300 text-sm">{inc.device}</div>
                    <div className="text-gray-600 text-xs">{inc.facility}</div>
                  </td>
                  <td className="px-5 py-3">
                    {inc.fault ? (
                      <span className="font-mono text-xs bg-gray-800 px-2 py-0.5 rounded">{inc.fault}</span>
                    ) : <span className="text-gray-600">—</span>}
                  </td>
                  <td className="px-5 py-3">
                    {inc.severity ? (
                      <span className={`text-xs font-medium ${severityColor[inc.severity]}`}>{inc.severity}</span>
                    ) : <span className="text-gray-600">—</span>}
                  </td>
                  <td className="px-5 py-3">
                    <div className={`flex items-center gap-1.5 ${outcomeColors[inc.outcome]}`}>
                      <OutcomeIcon className="h-3.5 w-3.5" />
                      <span className="text-xs">{inc.outcome.replace(/_/g, ' ')}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-xs text-gray-400">{formatDate(inc.started)}</td>
                  <td className="px-5 py-3 text-green-400 font-medium text-sm">{inc.elapsed}</td>
                  <td className="px-5 py-3">
                    <Link to={`/incidents/${inc.id}`} className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-xs whitespace-nowrap">
                      Trace <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  </td>
                </tr>
              )
            })}
            {incidents.length === 0 && (
              <tr>
                <td colSpan={8} className="px-5 py-10 text-center text-gray-500 text-sm">No incidents match the selected filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
