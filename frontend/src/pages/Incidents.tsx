import { Link } from 'react-router-dom'
import { AlertTriangle, CheckCircle, XCircle, ChevronRight } from 'lucide-react'

const DEMO_INCIDENTS = [
  { id: 'INC-2025-0847', device: 'KCX-NYC-0042', fault: 'KX-T2209-B', severity: 'HIGH', outcome: 'WORK_ORDER_DISPATCHED', started: '2025-01-15T14:32:00Z', elapsed: '38s' },
  { id: 'INC-2025-0831', device: 'KCX-CHI-0011', fault: 'KX-V1103-A', severity: 'MEDIUM', outcome: 'WORK_ORDER_DISPATCHED', started: '2025-01-15T11:14:00Z', elapsed: '41s' },
  { id: 'INC-2025-0819', device: 'KCX-NYC-0043', fault: null, severity: null, outcome: 'NO_FAULT', started: '2025-01-15T08:02:00Z', elapsed: '4s' },
  { id: 'INC-2025-0803', device: 'KCX-DFW-0008', fault: 'KX-E4412-A', severity: 'HIGH', outcome: 'BLOCKED_BY_SAFETY', started: '2025-01-15T06:48:00Z', elapsed: '29s' },
]

const outcomeIcon: Record<string, React.ElementType> = {
  WORK_ORDER_DISPATCHED: CheckCircle,
  NO_FAULT: CheckCircle,
  BLOCKED_BY_SAFETY: XCircle,
}

const outcomeColors: Record<string, string> = {
  WORK_ORDER_DISPATCHED: 'text-green-400',
  NO_FAULT: 'text-gray-400',
  BLOCKED_BY_SAFETY: 'text-red-400',
}

export default function Incidents() {
  return (
    <div className="p-6 space-y-5">
      <h1 className="text-2xl font-bold text-white">Incidents</h1>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wide">
              <th className="px-5 py-3 text-left">Incident ID</th>
              <th className="px-5 py-3 text-left">Device</th>
              <th className="px-5 py-3 text-left">Fault Code</th>
              <th className="px-5 py-3 text-left">Severity</th>
              <th className="px-5 py-3 text-left">Outcome</th>
              <th className="px-5 py-3 text-left">Response</th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {DEMO_INCIDENTS.map(inc => {
              const OutcomeIcon = outcomeIcon[inc.outcome] || AlertTriangle
              return (
                <tr key={inc.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                  <td className="px-5 py-3 font-mono text-gray-200">{inc.id}</td>
                  <td className="px-5 py-3 text-gray-300">{inc.device}</td>
                  <td className="px-5 py-3">
                    {inc.fault ? (
                      <span className="font-mono text-xs bg-gray-800 px-2 py-0.5 rounded">{inc.fault}</span>
                    ) : <span className="text-gray-600">—</span>}
                  </td>
                  <td className="px-5 py-3">
                    {inc.severity ? (
                      <span className={`text-xs font-medium ${inc.severity === 'HIGH' ? 'text-red-400' : 'text-amber-400'}`}>
                        {inc.severity}
                      </span>
                    ) : <span className="text-gray-600">—</span>}
                  </td>
                  <td className="px-5 py-3">
                    <div className={`flex items-center gap-2 ${outcomeColors[inc.outcome]}`}>
                      <OutcomeIcon className="h-4 w-4" />
                      <span className="text-xs">{inc.outcome.replace(/_/g, ' ')}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-green-400 font-medium">{inc.elapsed}</td>
                  <td className="px-5 py-3">
                    <Link to={`/incidents/${inc.id}`} className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-xs">
                      Trace <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
