import { ClipboardList, Clock, CheckCircle } from 'lucide-react'

const DEMO_WOS = [
  { id: 'WO-20250115-A9F2', incident: 'INC-2025-0847', device: 'KCX-NYC-0042', fault: 'KX-T2209-B', priority: 'HIGH', tech: 'Maria Santos', status: 'IN_PROGRESS', parts: ['P-2209', 'P-3301'], eta: '45 min' },
  { id: 'WO-20250115-B3C1', incident: 'INC-2025-0831', device: 'KCX-CHI-0011', fault: 'KX-V1103-A', priority: 'MEDIUM', tech: 'James Okafor', status: 'COMPLETED', parts: ['P-1103-SKF'], eta: 'Done' },
  { id: 'WO-20250114-D7F4', incident: 'INC-2025-0799', device: 'KCX-DFW-0008', fault: 'KX-P3301-C', priority: 'MEDIUM', tech: 'Lin Wei', status: 'COMPLETED', parts: ['P-STR-001'], eta: 'Done' },
]

export default function WorkOrders() {
  return (
    <div className="p-6 space-y-5">
      <h1 className="text-2xl font-bold text-white">Work Orders</h1>

      <div className="space-y-4">
        {DEMO_WOS.map(wo => (
          <div key={wo.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-3">
                  <ClipboardList className="h-5 w-5 text-blue-400" />
                  <span className="font-mono font-semibold text-white">{wo.id}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    wo.priority === 'HIGH' ? 'bg-red-900/50 text-red-300 border border-red-700' :
                    'bg-amber-900/50 text-amber-300 border border-amber-700'
                  }`}>{wo.priority}</span>
                </div>
                <div className="text-sm text-gray-400 mt-1 ml-8">{wo.device} · {wo.fault} · Incident {wo.incident}</div>
              </div>
              <div className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-full border ${
                wo.status === 'COMPLETED' ? 'bg-green-900/30 text-green-300 border-green-700' :
                'bg-blue-900/30 text-blue-300 border-blue-700'
              }`}>
                {wo.status === 'COMPLETED' ? <CheckCircle className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                {wo.status.replace('_', ' ')}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 text-sm ml-8">
              <div>
                <div className="text-xs text-gray-500 mb-1">Assigned To</div>
                <div className="text-gray-200">{wo.tech}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Parts Required</div>
                <div className="flex gap-1 flex-wrap">
                  {wo.parts.map(p => (
                    <span key={p} className="text-xs font-mono bg-gray-800 text-gray-300 px-2 py-0.5 rounded">{p}</span>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">ETA</div>
                <div className="text-gray-200">{wo.eta}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
