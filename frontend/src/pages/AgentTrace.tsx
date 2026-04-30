import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle, XCircle, ChevronRight, Clock, Shield, BookOpen, Activity } from 'lucide-react'
import { api } from '../utils/api'

const DEMO_TRACE = {
  incident_id: 'INC-2025-0847',
  device_id: 'KCX-NYC-0042',
  started_at: new Date(Date.now() - 38000).toISOString(),
  resolved_at: new Date().toISOString(),
  outcome: 'WORK_ORDER_DISPATCHED',
  work_order_id: 'WO-20250115-A9F2',
  stages: {
    diagnostic: {
      agent: 'DiagnosticLead',
      fault_code: 'KX-T2209-B',
      fault_description: 'Coolant Pump Seal Degradation — Thermal Escalation',
      severity: 'HIGH',
      confidence: 0.94,
      reasoning: 'Coolant flow declining 12.3% over 4h window (trend: -0.61 LPM/sample). Temperature rising 0.82°C/sample while ambient is stable. Current draw increasing 0.18 A/sample, consistent with pump working against reduced flow. Vibration shows minor elevation (+0.3 mm/s) — co-occurring bearing stress. Pattern matches KX-T2209-B pre-fault signature from training data.',
      llm_invoked: true,
      prompt_version: 'v1.2',
    },
    librarian: {
      agent: 'TechnicalLibrarian',
      fault_code: 'KX-T2209-B',
      faithfulness_score: 0.96,
      retrieval_count: 5,
      repair_steps: [
        { step: 1, action: 'Isolate and LOTO — engage lockout at unit disconnect switch, verify zero energy state at L1, L2, L3 [KCX-TSM-2024-REV3 §5.1]', safety_critical: true },
        { step: 2, action: 'Cool-down wait — minimum 15 minutes for coolant < 50°C [KCX-TSM-2024-REV3 §5.1]', safety_critical: true },
        { step: 3, action: 'Drain coolant loop (~8 liters) to catch basin [KCX-TSM-2024-REV3 §5.1]', safety_critical: false },
        { step: 4, action: 'Remove pump cover (4x M8 bolts, 24 Nm) and extract shaft seal using P-PULL-2209 [KCX-TSM-2024-REV3 §5.1]', safety_critical: false },
        { step: 5, action: 'Install new shaft seal P-2209 and O-ring set P-3301 [KCX-TSM-2024-REV3 §5.1]', safety_critical: false },
        { step: 6, action: 'Pressure test at 120 PSI for 10 minutes (acceptable loss < 2 PSI) [KCX-TSM-2024-REV3 §5.1]', safety_critical: true },
        { step: 7, action: 'Restore power and verify flow ≥ 175 LPM within 3 minutes [KCX-TSM-2024-REV3 §5.1]', safety_critical: false },
      ],
      parts_list: [
        { part_number: 'P-2209', part_name: 'Coolant Pump Shaft Seal', quantity: 1 },
        { part_number: 'P-3301', part_name: 'O-Ring Set (12-piece)', quantity: 1 },
      ],
      estimated_duration_minutes: 42,
    },
    safety_audit: {
      agent: 'SafetyAuditor',
      decision: 'GO',
      reason: 'Voltage confirmed at 420V — within safe range for LOTO and pump work (threshold: ≤ 480V). Coolant temperature at 88°C exceeds immediate work threshold; 15-minute cooldown prerequisite enforced in Step 2. All safety prerequisites are confirmable. Arc flash rating: Class 2 PPE (440–480V range). Approving with standard LOTO protocol.',
      ppe_required: 'Class 2 arc flash suit (8 cal/cm²), LOTO device, chemical splash goggles',
      voltage_checked: 420.0,
      arc_flash_rating: '440–480V: Class 2 PPE (8 cal/cm²)',
      hard_rule_triggered: false,
    },
    work_order: {
      work_order_id: 'WO-20250115-A9F2',
      status: 'DISPATCHED',
    },
  },
}

function StageCard({ title, icon: Icon, status, children }: {
  title: string; icon: React.ElementType; status: 'pass' | 'fail' | 'info'; children: React.ReactNode
}) {
  return (
    <div className={`bg-gray-900 border rounded-xl overflow-hidden ${
      status === 'pass' ? 'border-green-800' : status === 'fail' ? 'border-red-800' : 'border-gray-800'
    }`}>
      <div className={`px-5 py-3 flex items-center gap-3 ${
        status === 'pass' ? 'bg-green-900/20' : status === 'fail' ? 'bg-red-900/20' : 'bg-gray-800/50'
      }`}>
        <Icon className="h-4 w-4 text-gray-400" />
        <span className="font-semibold text-sm text-white">{title}</span>
        {status === 'pass' && <CheckCircle className="h-4 w-4 text-green-400 ml-auto" />}
        {status === 'fail' && <XCircle className="h-4 w-4 text-red-400 ml-auto" />}
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

export default function AgentTrace() {
  const { id } = useParams()
  const { data: trace = DEMO_TRACE } = useQuery({
    queryKey: ['incident', id],
    queryFn: () => api.get(`/incidents/${id}`).then(r => r.data),
    enabled: !!id && !id.startsWith('demo'),
    initialData: DEMO_TRACE,
  })

  const stages = trace.stages
  const elapsed = trace.resolved_at
    ? ((new Date(trace.resolved_at).getTime() - new Date(trace.started_at).getTime()) / 1000).toFixed(1)
    : '—'

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
        <span>Incidents</span>
        <ChevronRight className="h-4 w-4" />
        <span className="text-white">{trace.incident_id}</span>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">{trace.incident_id}</h1>
          <p className="text-gray-400 text-sm mt-1">{trace.device_id} · Pipeline completed in {elapsed}s</p>
        </div>
        <div className="flex items-center gap-2 text-sm bg-green-900/40 text-green-300 px-4 py-2 rounded-full border border-green-700">
          <CheckCircle className="h-4 w-4" />
          Work order dispatched
        </div>
      </div>

      {/* Stage 1: Diagnostic */}
      <StageCard title="Stage 1 — Diagnostic Lead" icon={Activity} status="pass">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-xs bg-red-900/50 text-red-300 border border-red-700 px-2 py-1 rounded font-mono">
              {stages.diagnostic.fault_code}
            </span>
            <span className="text-sm text-white">{stages.diagnostic.fault_description}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ml-auto ${
              stages.diagnostic.severity === 'HIGH' ? 'bg-red-900/50 text-red-300' : 'bg-amber-900/50 text-amber-300'
            }`}>
              {stages.diagnostic.severity}
            </span>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-sm text-gray-300 leading-relaxed">
            <div className="text-xs text-gray-500 mb-2">Chain-of-thought reasoning</div>
            {stages.diagnostic.reasoning}
          </div>
          <div className="flex gap-4 text-xs text-gray-500">
            <span>Confidence: <span className="text-green-400 font-medium">{(stages.diagnostic.confidence * 100).toFixed(0)}%</span></span>
            <span>Prompt: <span className="text-gray-300">{stages.diagnostic.prompt_version}</span></span>
          </div>
        </div>
      </StageCard>

      {/* Stage 2: Librarian */}
      <StageCard title="Stage 2 — Technical Librarian (Hybrid RAG)" icon={BookOpen} status="pass">
        <div className="space-y-4">
          <div className="flex gap-4 text-xs text-gray-500">
            <span>Faithfulness: <span className="text-green-400 font-medium">{(stages.librarian.faithfulness_score * 100).toFixed(0)}%</span></span>
            <span>Chunks retrieved: <span className="text-gray-300">{stages.librarian.retrieval_count}</span></span>
            <span>Duration: <span className="text-gray-300">{stages.librarian.estimated_duration_minutes} min</span></span>
          </div>
          <div className="space-y-2">
            {stages.librarian.repair_steps.map((step: { step: number; action: string; safety_critical: boolean }) => (
              <div key={step.step} className={`flex gap-3 p-2 rounded text-sm ${
                step.safety_critical ? 'bg-amber-900/20 border border-amber-800/50' : 'bg-gray-800/50'
              }`}>
                <span className="text-gray-500 w-5 shrink-0">{step.step}.</span>
                <span className="text-gray-200">{step.action}</span>
                {step.safety_critical && (
                  <Shield className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" />
                )}
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-2">
            {stages.librarian.parts_list.map((p: { part_number: string; quantity: number }) => (
              <span key={p.part_number} className="text-xs bg-blue-900/30 text-blue-300 border border-blue-800/50 px-2 py-1 rounded font-mono">
                {p.part_number} × {p.quantity}
              </span>
            ))}
          </div>
        </div>
      </StageCard>

      {/* Stage 3: Safety Auditor */}
      <StageCard title="Stage 3 — Safety Auditor (Adversarial Gate)" icon={Shield}
        status={stages.safety_audit.decision === 'GO' ? 'pass' : 'fail'}>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className={`text-sm font-bold px-3 py-1 rounded ${
              stages.safety_audit.decision === 'GO'
                ? 'bg-green-900/50 text-green-300 border border-green-700'
                : 'bg-red-900/50 text-red-300 border border-red-700'
            }`}>
              {stages.safety_audit.decision}
            </span>
            <span className="text-xs text-gray-400">V={stages.safety_audit.voltage_checked}V · {stages.safety_audit.arc_flash_rating}</span>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-sm text-gray-300 leading-relaxed">
            {stages.safety_audit.reason}
          </div>
          <div className="text-xs text-amber-300 bg-amber-900/20 border border-amber-800/50 px-3 py-2 rounded">
            PPE Required: {stages.safety_audit.ppe_required}
          </div>
        </div>
      </StageCard>

      {/* Stage 4: Work Order */}
      <StageCard title="Stage 4 — Work Order Generated" icon={Clock} status="pass">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-mono text-blue-300">{stages.work_order.work_order_id}</div>
            <div className="text-xs text-gray-500 mt-1">Dispatched to on-call technician team</div>
          </div>
          <span className="text-xs bg-green-900/50 text-green-300 border border-green-700 px-3 py-1.5 rounded-full">
            DISPATCHED
          </span>
        </div>
      </StageCard>
    </div>
  )
}
