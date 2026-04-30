import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle, XCircle, ChevronRight, Clock, Shield, BookOpen, Activity, AlertTriangle } from 'lucide-react'
import { api } from '../utils/api'

// ── Incident metadata — drives trace template selection ───────────────────────

const INCIDENT_META: Record<string, {
  device_id: string; outcome: string; fault_code: string | null
  work_order_id?: string; started_ago_s: number; elapsed_s: number
}> = {
  'INC-2026-0847': { device_id: 'KCX-NYC-0042', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-T2209-B', work_order_id: 'WO-20260430-A9F2', started_ago_s: 2280, elapsed_s: 38 },
  'INC-2026-0846': { device_id: 'KCX-NYC-0044', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-V1103-A', work_order_id: 'WO-20260430-B3C1', started_ago_s: 8220, elapsed_s: 44 },
  'INC-2026-0845': { device_id: 'KCX-NYC-0045', outcome: 'BLOCKED_BY_SAFETY',    fault_code: 'KX-E4412-A', started_ago_s: 15840, elapsed_s: 31 },
  'INC-2026-0843': { device_id: 'KCX-CHI-0011', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-V1103-A', work_order_id: 'WO-20260429-C7D4', started_ago_s: 68640, elapsed_s: 41 },
  'INC-2026-0841': { device_id: 'KCX-DFW-0009', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-P3301-C', work_order_id: 'WO-20260429-E2A8', started_ago_s: 95880, elapsed_s: 27 },
  'INC-2026-0839': { device_id: 'KCX-LAX-0002', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-T2209-B', work_order_id: 'WO-20260428-F4B9', started_ago_s: 163500, elapsed_s: 39 },
  'INC-2026-0836': { device_id: 'KCX-NYC-0043', outcome: 'NO_FAULT',             fault_code: null,          started_ago_s: 216060, elapsed_s: 5 },
  'INC-2026-0833': { device_id: 'KCX-DFW-0008', outcome: 'BLOCKED_BY_SAFETY',    fault_code: 'KX-E4412-A', started_ago_s: 303180, elapsed_s: 29 },
  'INC-2026-0829': { device_id: 'KCX-CHI-0012', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-F2208-B', work_order_id: 'WO-20260426-G1K3', started_ago_s: 469920, elapsed_s: 22 },
  'INC-2026-0825': { device_id: 'KCX-SEA-0001', outcome: 'NO_FAULT',             fault_code: null,          started_ago_s: 642720, elapsed_s: 4 },
  'INC-2026-0820': { device_id: 'KCX-NYC-0042', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-T2209-B', work_order_id: 'WO-20260423-H8J2', started_ago_s: 816300, elapsed_s: 36 },
  'INC-2026-0815': { device_id: 'KCX-CHI-0013', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-V1103-A', work_order_id: 'WO-20260422-J5L7', started_ago_s: 901200, elapsed_s: 43 },
  'INC-2026-0811': { device_id: 'KCX-LAX-0001', outcome: 'NO_FAULT',             fault_code: null,          started_ago_s: 986400, elapsed_s: 4 },
  'INC-2026-0807': { device_id: 'KCX-NYC-0045', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-P3301-C', work_order_id: 'WO-20260419-K2M4', started_ago_s: 1157460, elapsed_s: 25 },
  'INC-2026-0803': { device_id: 'KCX-DFW-0008', outcome: 'BLOCKED_BY_SAFETY',    fault_code: 'KX-E4412-A', started_ago_s: 1244520, elapsed_s: 30 },
  'INC-2026-0799': { device_id: 'KCX-NYC-0043', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-C5501-A', work_order_id: 'WO-20260416-L9N6', started_ago_s: 1415700, elapsed_s: 33 },
  'INC-2026-0793': { device_id: 'KCX-CHI-0011', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-T2209-B', work_order_id: 'WO-20260414-M3P8', started_ago_s: 1588920, elapsed_s: 40 },
  'INC-2026-0788': { device_id: 'KCX-DFW-0009', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-P3301-C', work_order_id: 'WO-20260412-N7Q1', started_ago_s: 1760700, elapsed_s: 28 },
  'INC-2026-0781': { device_id: 'KCX-LAX-0002', outcome: 'WORK_ORDER_DISPATCHED', fault_code: 'KX-V1103-A', work_order_id: 'WO-20260410-P3R5', started_ago_s: 1934100, elapsed_s: 45 },
  'INC-2026-0774': { device_id: 'KCX-SEA-0001', outcome: 'BLOCKED_BY_SAFETY',    fault_code: 'KX-E4412-A', started_ago_s: 2116440, elapsed_s: 31 },
}

// ── Trace stage templates keyed by fault_code ─────────────────────────────────

const DIAG: Record<string, object> = {
  'KX-T2209-B-HIGH': {
    fault_code: 'KX-T2209-B', fault_description: 'Coolant Pump Seal Degradation — Thermal Escalation',
    severity: 'HIGH', confidence: 0.94, llm_invoked: true, prompt_version: 'v1.2',
    reasoning: 'Coolant flow declining 12.3% over 4h window (trend: −0.61 LPM/sample). Temperature rising 0.82°C/sample while ambient remains stable at 22°C. Current draw increasing 0.18 A/sample — pump motor working against reduced flow resistance. Vibration elevation (+0.3 mm/s) indicates co-occurring bearing stress from pump cavitation. Pattern matches KX-T2209-B pre-fault signature at 94% confidence. Early detection at hour 2 — 4h before threshold breach.',
  },
  'KX-T2209-B-MEDIUM': {
    fault_code: 'KX-T2209-B', fault_description: 'Coolant Pump Seal Degradation — Early Stage',
    severity: 'MEDIUM', confidence: 0.87, llm_invoked: true, prompt_version: 'v1.2',
    reasoning: 'Flow rate declining 7.8% over 3h window (trend: −0.38 LPM/sample). Temperature rising modestly at 0.44°C/sample; still below thermal warning threshold but trending upward. Current draw elevated +0.09 A/sample. Vibration within normal range. Pattern consistent with early KX-T2209-B — seal wear detectable before significant coolant restriction. Recommend scheduling maintenance within 12h.',
  },
  'KX-V1103-A': {
    fault_code: 'KX-V1103-A', fault_description: 'Pump Bearing Micro-Failure — Vibration Escalation',
    severity: 'MEDIUM', confidence: 0.91, llm_invoked: true, prompt_version: 'v1.2',
    reasoning: 'Vibration escalating at 0.31 mm/s/sample over 6h window; currently 3.8 mm/s (normal: 1.2 mm/s). RPM coefficient of variation = 0.038, exceeding 0.03 instability threshold — rotor imbalance consistent with bearing wear. Temperature elevated +7.2°C above baseline; flow and voltage nominal. Pattern matches KX-V1103-A bearing fatigue signature. 48h deferral window available per §6.3 before mandatory shutdown.',
  },
  'KX-E4412-A': {
    fault_code: 'KX-E4412-A', fault_description: 'Supply Voltage Sag — Motor Underperformance',
    severity: 'HIGH', confidence: 0.97, llm_invoked: true, prompt_version: 'v1.2',
    reasoning: 'Supply voltage dropped from 478V baseline to 398V over 90min window (−16.7%). Current draw compensating: +22.4% above baseline. Power factor degraded from 0.92 to 0.79. Temperature mildly elevated (+5.8°C) from motor inefficiency. Vibration and flow nominal — confirms this is a facility power quality event, not mechanical failure. Root cause: PDU upstream — requires facility electrical team intervention, NOT onsite repair.',
  },
  'KX-P3301-C': {
    fault_code: 'KX-P3301-C', fault_description: 'Coolant Pressure Drop — Strainer Blockage',
    severity: 'MEDIUM', confidence: 0.89, llm_invoked: true, prompt_version: 'v1.2',
    reasoning: 'Flow rate declining 18.4% over 5h window (trend: −0.52 LPM/sample), currently 151 LPM. Key discriminator: temperature rising only mildly (+8.3°C) — significantly less than the 40–50°C rise expected with seal failure (KX-T2209-B). Vibration and current stable. Flow/temperature ratio diagnostic: 0.62 (blockage pattern) vs 0.18 (seal failure pattern). Strainer restriction is the highest-probability root cause.',
  },
  'KX-F2208-B': {
    fault_code: 'KX-F2208-B', fault_description: 'Coolant Flow Sensor Fault — Calibration Drift',
    severity: 'LOW', confidence: 0.82, llm_invoked: false, prompt_version: 'v1.2',
    reasoning: 'Flow readings showing erratic oscillation: range 143–231 LPM over last 4h against expected 185 ±5 LPM. Oscillation pattern does not correlate with temperature, current, or vibration changes — indicating sensor error rather than true flow change. Coefficient of variation for flow: 0.18 (threshold: 0.08). Temperature, voltage, vibration all within spec. Statistical pattern matches KX-F2208-B sensor drift signature.',
  },
  'KX-C5501-A': {
    fault_code: 'KX-C5501-A', fault_description: 'Control Board Communication Fault',
    severity: 'LOW', confidence: 0.78, llm_invoked: false, prompt_version: 'v1.2',
    reasoning: 'Timestamp gaps detected in telemetry stream: 3 missing readings over 2h window (normal: 0). CAN bus message retransmit counter elevated (18 retransmits/h vs baseline 0–2). All sensor readings nominal when present — not a physical equipment fault. Pattern consistent with KX-C5501-A communication degradation. Firmware v3.2.0 on this unit is below current 3.2.1 — likely root cause.',
  },
}

const LIBRARIAN: Record<string, object> = {
  'KX-T2209-B': {
    fault_code: 'KX-T2209-B', faithfulness_score: 0.96, retrieval_count: 5,
    estimated_duration_minutes: 42,
    parts_list: [
      { part_number: 'P-2209', part_name: 'Coolant Pump Shaft Seal', quantity: 1 },
      { part_number: 'P-3301', part_name: 'O-Ring Set (12-piece)', quantity: 1 },
    ],
    repair_steps: [
      { step: 1, action: 'Isolate and LOTO — engage lockout at unit disconnect switch, verify zero energy at L1, L2, L3 [KCX-TSM-2024-REV3 §5.1]', safety_critical: true },
      { step: 2, action: 'Cool-down hold — minimum 15 minutes until coolant temperature < 50°C [KCX-TSM-2024-REV3 §5.1]', safety_critical: true },
      { step: 3, action: 'Drain coolant loop (~8 litres) to service catch basin [KCX-TSM-2024-REV3 §5.1]', safety_critical: false },
      { step: 4, action: 'Remove pump cover (4× M8 bolts, 24 Nm cross-pattern) using P-PULL-2209 [KCX-TSM-2024-REV3 §5.1]', safety_critical: false },
      { step: 5, action: 'Install new shaft seal P-2209 (white face toward coolant) and O-ring set P-3301 [KCX-TSM-2024-REV3 §5.1]', safety_critical: false },
      { step: 6, action: 'Pressure test at 120 PSI for 10 minutes — acceptable loss < 2 PSI [KCX-TSM-2024-REV3 §5.1]', safety_critical: true },
      { step: 7, action: 'Restore power and verify coolant flow ≥ 175 LPM within 3 minutes [KCX-TSM-2024-REV3 §5.1]', safety_critical: false },
    ],
  },
  'KX-V1103-A': {
    fault_code: 'KX-V1103-A', faithfulness_score: 0.93, retrieval_count: 4,
    estimated_duration_minutes: 65,
    parts_list: [
      { part_number: 'P-1103-SKF', part_name: 'Deep Groove Ball Bearing 6204-2RS', quantity: 2 },
    ],
    repair_steps: [
      { step: 1, action: 'Schedule maintenance window — unit may continue at reduced capacity for up to 48h [KCX-TSM-2024-REV3 §6.3]', safety_critical: false },
      { step: 2, action: 'Verify voltage < 480V before opening motor end-cap; apply LOTO [KCX-TSM-2024-REV3 §6.1]', safety_critical: true },
      { step: 3, action: 'Remove motor end-cap (8× M6 bolts, 12 Nm) — NOTE: bolts at 3 o\'clock and 9 o\'clock are 65mm, not 45mm [KCX-TSM-2024-REV3 §6.2]', safety_critical: false },
      { step: 4, action: 'Extract worn bearing using P-1103-PULLER tool; discard old bearing [KCX-TSM-2024-REV3 §6.2]', safety_critical: false },
      { step: 5, action: 'Press-fit pre-lubricated replacement bearing P-1103-SKF into housing [KCX-TSM-2024-REV3 §6.2]', safety_critical: false },
      { step: 6, action: 'Re-torque end-cap bolts to 12 Nm and replace long bolts at correct positions [KCX-TSM-2024-REV3 §6.2]', safety_critical: false },
      { step: 7, action: 'Power-on and verify vibration ≤ 1.5 mm/s and RPM 1750 ±25 [KCX-TSM-2024-REV3 §6.4]', safety_critical: false },
    ],
  },
  'KX-E4412-A': {
    fault_code: 'KX-E4412-A', faithfulness_score: 0.98, retrieval_count: 3,
    estimated_duration_minutes: 18,
    parts_list: [],
    repair_steps: [
      { step: 1, action: 'Contact facility electrical team — DO NOT perform PDU repairs onsite [KCX-TSM-2024-REV3 §8.1]', safety_critical: true },
      { step: 2, action: 'Log voltage readings every 15 minutes in incident record [KCX-TSM-2024-REV3 §8.2]', safety_critical: false },
      { step: 3, action: 'If voltage drops below 420V, execute graceful unit shutdown per §8.2 procedure [KCX-TSM-2024-REV3 §8.2]', safety_critical: true },
      { step: 4, action: 'Coordinate with UPS bypass team if sustained sag exceeds 30 minutes [KCX-TSM-2024-REV3 §8.3]', safety_critical: false },
    ],
  },
  'KX-P3301-C': {
    fault_code: 'KX-P3301-C', faithfulness_score: 0.91, retrieval_count: 4,
    estimated_duration_minutes: 28,
    parts_list: [
      { part_number: 'P-STR-001', part_name: 'Coolant Strainer Screen (50-micron)', quantity: 1 },
    ],
    repair_steps: [
      { step: 1, action: 'Run high-velocity flush at 120% pump speed for 5 minutes [KCX-TSM-2024-REV3 §5.2]', safety_critical: false },
      { step: 2, action: 'Access strainer housing via M32 fitting; inspect screen P-STR-001 [KCX-TSM-2024-REV3 §5.2]', safety_critical: false },
      { step: 3, action: 'Replace strainer screen if blockage > 30%; re-seat M32 fitting to 45 Nm [KCX-TSM-2024-REV3 §5.2]', safety_critical: false },
      { step: 4, action: 'Verify all valve positions per §5.1 schematic [KCX-TSM-2024-REV3 §5.2]', safety_critical: false },
      { step: 5, action: 'Monitor flow rate for 30 minutes post-flush — target ≥ 175 LPM [KCX-TSM-2024-REV3 §5.2]', safety_critical: false },
    ],
  },
  'KX-F2208-B': {
    fault_code: 'KX-F2208-B', faithfulness_score: 0.88, retrieval_count: 3,
    estimated_duration_minutes: 22,
    parts_list: [
      { part_number: 'P-2208', part_name: 'Ultrasonic Flow Sensor', quantity: 1 },
    ],
    repair_steps: [
      { step: 1, action: 'Verify sensor wiring harness connections at J-14 connector on control board [KCX-TSM-2024-REV3 §9.1]', safety_critical: false },
      { step: 2, action: 'Clean ultrasonic transducer faces with isopropyl alcohol swab [KCX-TSM-2024-REV3 §9.2]', safety_critical: false },
      { step: 3, action: 'Compare sensor P-2208 reading against inline reference flow meter [KCX-TSM-2024-REV3 §9.3]', safety_critical: false },
      { step: 4, action: 'Replace sensor P-2208 if calibration deviation > 5% [KCX-TSM-2024-REV3 §9.3]', safety_critical: false },
    ],
  },
  'KX-C5501-A': {
    fault_code: 'KX-C5501-A', faithfulness_score: 0.85, retrieval_count: 3,
    estimated_duration_minutes: 35,
    parts_list: [
      { part_number: 'P-CB-5501', part_name: 'Primary Control Board Assembly', quantity: 1 },
    ],
    repair_steps: [
      { step: 1, action: 'Power cycle control board — hold RST button for 5 seconds until LED flashes amber [KCX-TSM-2024-REV3 §10.1]', safety_critical: false },
      { step: 2, action: 'Check CAN bus termination resistors at each network end (must read 120Ω) [KCX-TSM-2024-REV3 §10.2]', safety_critical: false },
      { step: 3, action: 'Update firmware to v3.2.1 if currently < 3.2.1 (see release notes) [KCX-TSM-2024-REV3 §10.3]', safety_critical: false },
      { step: 4, action: 'Replace control board P-CB-5501 if fault persists after firmware update [KCX-TSM-2024-REV3 §10.4]', safety_critical: false },
    ],
  },
}

const SAFETY: Record<string, object> = {
  'KX-T2209-B-GO': {
    decision: 'GO', hard_rule_triggered: false, voltage_checked: 420.0,
    arc_flash_rating: '440–480V: Class 2 PPE (8 cal/cm²)',
    ppe_required: 'Class 2 arc flash suit (8 cal/cm²), LOTO device, chemical splash goggles',
    reason: 'Voltage confirmed at 420V — within safe range for LOTO and pump work (threshold: ≤ 480V). Coolant temperature above immediate work threshold; 15-minute cool-down enforced in Step 2 of repair procedure. Arc flash rating Class 2 (440–480V range). All safety prerequisites confirmable. Approving with standard LOTO protocol.',
  },
  'KX-T2209-B-GO-2': {
    decision: 'GO', hard_rule_triggered: false, voltage_checked: 461.0,
    arc_flash_rating: '440–480V: Class 2 PPE (8 cal/cm²)',
    ppe_required: 'Class 2 arc flash suit (8 cal/cm²), LOTO device, chemical splash goggles, coolant-resistant gloves',
    reason: 'Voltage at 461V — within safe threshold for seal/pump work. Coolant temperature requires 15-minute cool-down (Step 2 prerequisite). Pump must be fully de-energised and LOTO verified before cover removal. Arc flash Class 2 at this voltage range. GO with cool-down and LOTO prerequisites enforced.',
  },
  'KX-V1103-A-GO': {
    decision: 'GO_WITH_CONDITIONS', hard_rule_triggered: false, voltage_checked: 477.0,
    arc_flash_rating: '440–480V: Class 2 PPE (8 cal/cm²)',
    ppe_required: 'Class 2 arc flash suit (8 cal/cm²), LOTO device, safety glasses, gloves',
    reason: 'Voltage at 477V — below 480V LOTO threshold, bearing access permitted. Vibration at 3.8 mm/s is below the 6.0 mm/s bearing-work limit. Unit qualifies for the 48-hour deferral window per §6.3. GO WITH CONDITIONS: (1) Schedule within 48h, (2) full LOTO before end-cap removal, (3) verify voltage < 480V immediately before starting work.',
  },
  'KX-E4412-A-NOGO': {
    decision: 'NO_GO', hard_rule_triggered: true, voltage_checked: 398.0,
    arc_flash_rating: '> 480V baseline — STOP: facility electrical required',
    ppe_required: 'No onsite work permitted',
    reason: 'HARD RULE VIOLATION: Voltage SAG detected at 398V — facility supply power is unstable. Any onsite electrical work is PROHIBITED until facility electrical team stabilises the supply. This is NOT a unit-level repair. DO NOT open any electrical panels or attempt LOTO in an unstable supply condition. Escalate immediately to facility electrical team and log voltage readings every 15 minutes.',
  },
  'KX-E4412-A-NOGO-2': {
    decision: 'NO_GO', hard_rule_triggered: true, voltage_checked: 411.0,
    arc_flash_rating: 'Unstable supply — arc flash risk unquantifiable',
    ppe_required: 'No onsite work permitted until supply stabilised',
    reason: 'HARD RULE VIOLATION: Supply voltage at 411V from a baseline of 478V indicates active facility power event. Voltage is fluctuating — transient readings between 405–430V detected. Arc flash risk cannot be quantified under unstable supply conditions. All onsite work PROHIBITED. Facility electrical team must resolve supply voltage before any unit access. Graceful shutdown may be required if sustained sag continues.',
  },
  'KX-P3301-C-GO': {
    decision: 'GO', hard_rule_triggered: false, voltage_checked: 479.0,
    arc_flash_rating: '440–480V: Class 2 PPE (8 cal/cm²)',
    ppe_required: 'Safety glasses, coolant-resistant gloves, Class 1 arc flash (4 cal/cm²)',
    reason: 'Strainer access does not require LOTO — M32 fitting is on the coolant loop, no electrical exposure. Voltage nominal at 479V. Coolant temperature within acceptable range for maintenance access. No hard safety rules triggered. Standard maintenance PPE sufficient for strainer inspection and flush procedure.',
  },
  'KX-F2208-B-GO': {
    decision: 'GO', hard_rule_triggered: false, voltage_checked: 481.0,
    arc_flash_rating: '440–480V: Class 2 PPE (8 cal/cm²)',
    ppe_required: 'ESD wristband, safety glasses, standard electrical PPE',
    reason: 'Sensor replacement is low-risk — J-14 connector is on the control board, 24V signal circuit only. Unit voltage nominal at 481V; sensor circuit is isolated from mains. No thermal hazard. Go with standard ESD precautions.',
  },
  'KX-C5501-A-GO': {
    decision: 'GO', hard_rule_triggered: false, voltage_checked: 479.0,
    arc_flash_rating: '440–480V: Class 2 PPE (8 cal/cm²)',
    ppe_required: 'ESD wristband, safety glasses',
    reason: 'Control board firmware update and RST cycle carry no physical hazard. Voltage nominal at 479V. Board replacement, if required, involves only the 24V logic circuit (mains-isolated). No LOTO required for RST procedure; LOTO required only if board replacement proceeds. Go with standard ESD protocol.',
  },
}

// ── Build a complete trace for a given incident ID ────────────────────────────

function buildTrace(incidentId: string) {
  const meta = INCIDENT_META[incidentId]
  if (!meta) return buildDefaultTrace(incidentId)

  const now = Date.now()
  const started_at = new Date(now - meta.started_ago_s * 1000).toISOString()
  const resolved_at = new Date(now - meta.started_ago_s * 1000 + meta.elapsed_s * 1000).toISOString()

  const { device_id, outcome, fault_code, work_order_id } = meta

  if (outcome === 'NO_FAULT') {
    return {
      incident_id: incidentId, device_id, started_at, resolved_at, outcome,
      stages: {
        diagnostic: {
          agent: 'DiagnosticLead', fault_code: null, fault_description: 'No fault detected',
          severity: 'LOW', confidence: 0.92, llm_invoked: false, prompt_version: 'v1.2',
          reasoning: 'All sensor readings within normal operating range. Temperature, flow, vibration, and voltage trending nominal over the 2h analysis window. No anomalies detected by statistical threshold checks. LLM not invoked — clean data pipeline. Incident closed as NO_FAULT.',
        },
      },
    }
  }

  // Pick diagnostic variant
  const diagKey = fault_code === 'KX-T2209-B'
    ? (INCIDENT_META[incidentId]?.elapsed_s <= 39 ? 'KX-T2209-B-HIGH' : 'KX-T2209-B-MEDIUM')
    : fault_code!

  const NO_GO_VARIANT: Record<string, string> = {
    'INC-2026-0845': 'KX-E4412-A-NOGO',
    'INC-2026-0833': 'KX-E4412-A-NOGO-2',
    'INC-2026-0803': 'KX-E4412-A-NOGO',
    'INC-2026-0774': 'KX-E4412-A-NOGO-2',
  }
  const safetyKey = outcome === 'BLOCKED_BY_SAFETY'
    ? (NO_GO_VARIANT[incidentId] || 'KX-E4412-A-NOGO')
    : fault_code === 'KX-T2209-B'
      ? (INCIDENT_META[incidentId]?.elapsed_s <= 39 ? 'KX-T2209-B-GO' : 'KX-T2209-B-GO-2')
      : fault_code === 'KX-V1103-A' ? 'KX-V1103-A-GO'
      : fault_code === 'KX-P3301-C' ? 'KX-P3301-C-GO'
      : fault_code === 'KX-F2208-B' ? 'KX-F2208-B-GO'
      : 'KX-C5501-A-GO'

  const stages: Record<string, object> = {
    diagnostic: { agent: 'DiagnosticLead', ...DIAG[diagKey] },
    librarian:  { agent: 'TechnicalLibrarian', incident_id: incidentId, ...LIBRARIAN[fault_code!] },
    safety_audit: { agent: 'SafetyAuditor', incident_id: incidentId, ...SAFETY[safetyKey] },
  }

  if (outcome === 'WORK_ORDER_DISPATCHED' && work_order_id) {
    stages.work_order = { work_order_id, status: 'DISPATCHED' }
  }

  return { incident_id: incidentId, device_id, started_at, resolved_at, outcome, work_order_id, stages }
}

function buildDefaultTrace(incidentId: string) {
  const now = Date.now()
  return {
    incident_id: incidentId, device_id: 'KCX-NYC-0042',
    started_at: new Date(now - 38000).toISOString(),
    resolved_at: new Date(now).toISOString(),
    outcome: 'WORK_ORDER_DISPATCHED', work_order_id: 'WO-20260430-A9F2',
    stages: {
      diagnostic: { agent: 'DiagnosticLead', ...DIAG['KX-T2209-B-HIGH'] },
      librarian:  { agent: 'TechnicalLibrarian', ...LIBRARIAN['KX-T2209-B'] },
      safety_audit: { agent: 'SafetyAuditor', ...SAFETY['KX-T2209-B-GO'] },
      work_order: { work_order_id: 'WO-20260430-A9F2', status: 'DISPATCHED' },
    },
  }
}

// ── UI components ─────────────────────────────────────────────────────────────

function StageCard({ title, icon: Icon, status, children }: {
  title: string; icon: React.ElementType; status: 'pass' | 'fail' | 'warn' | 'info'; children: React.ReactNode
}) {
  const border = status === 'pass' ? 'border-green-800' : status === 'fail' ? 'border-red-800' : status === 'warn' ? 'border-amber-800' : 'border-gray-800'
  const header = status === 'pass' ? 'bg-green-900/20' : status === 'fail' ? 'bg-red-900/20' : status === 'warn' ? 'bg-amber-900/20' : 'bg-gray-800/50'
  return (
    <div className={`bg-gray-900 border rounded-xl overflow-hidden ${border}`}>
      <div className={`px-5 py-3 flex items-center gap-3 ${header}`}>
        <Icon className="h-4 w-4 text-gray-400" />
        <span className="font-semibold text-sm text-white">{title}</span>
        {status === 'pass' && <CheckCircle className="h-4 w-4 text-green-400 ml-auto" />}
        {status === 'fail' && <XCircle className="h-4 w-4 text-red-400 ml-auto" />}
        {status === 'warn' && <AlertTriangle className="h-4 w-4 text-amber-400 ml-auto" />}
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

export default function AgentTrace() {
  const { id } = useParams()
  const fallback = buildTrace(id || '')

  const { data: trace = fallback } = useQuery({
    queryKey: ['incident', id],
    queryFn: () => api.get(`/incidents/${id}`).then(r => r.data),
    enabled: !!id && !id.startsWith('INC-2026-'),
    initialData: fallback,
  })

  const stages = trace.stages || {}
  const elapsed = trace.resolved_at
    ? ((new Date(trace.resolved_at).getTime() - new Date(trace.started_at).getTime()) / 1000).toFixed(1)
    : '—'

  const isBlocked = trace.outcome === 'BLOCKED_BY_SAFETY'
  const isNoFault = trace.outcome === 'NO_FAULT'
  const isDispatched = trace.outcome === 'WORK_ORDER_DISPATCHED'

  const diag = stages.diagnostic || {}
  const lib = stages.librarian || {}
  const audit = stages.safety_audit || {}
  const wo = stages.work_order || {}

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
        <Link to="/incidents" className="hover:text-gray-300">Incidents</Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-white font-mono">{trace.incident_id}</span>
      </div>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-white">{trace.incident_id}</h1>
          <p className="text-gray-400 text-sm mt-1">{trace.device_id} · Pipeline completed in {elapsed}s</p>
        </div>
        {isDispatched && (
          <div className="flex items-center gap-2 text-sm bg-green-900/40 text-green-300 px-4 py-2 rounded-full border border-green-700">
            <CheckCircle className="h-4 w-4" /> Work order dispatched
          </div>
        )}
        {isBlocked && (
          <div className="flex items-center gap-2 text-sm bg-red-900/40 text-red-300 px-4 py-2 rounded-full border border-red-700">
            <XCircle className="h-4 w-4" /> Blocked by safety gate
          </div>
        )}
        {isNoFault && (
          <div className="flex items-center gap-2 text-sm bg-gray-800 text-gray-400 px-4 py-2 rounded-full border border-gray-700">
            <CheckCircle className="h-4 w-4" /> No fault detected
          </div>
        )}
      </div>

      {/* Stage 1: Diagnostic */}
      <StageCard title="Stage 1 — Diagnostic Lead" icon={Activity} status="pass">
        <div className="space-y-3">
          <div className="flex items-center gap-3 flex-wrap">
            {diag.fault_code ? (
              <span className="text-xs bg-red-900/50 text-red-300 border border-red-700 px-2 py-1 rounded font-mono">
                {diag.fault_code}
              </span>
            ) : (
              <span className="text-xs bg-gray-700 text-gray-400 px-2 py-1 rounded">No fault code</span>
            )}
            <span className="text-sm text-white">{diag.fault_description}</span>
            {diag.severity && (
              <span className={`text-xs px-2 py-0.5 rounded-full ml-auto ${
                diag.severity === 'HIGH' ? 'bg-red-900/50 text-red-300' :
                diag.severity === 'MEDIUM' ? 'bg-amber-900/50 text-amber-300' :
                'bg-blue-900/50 text-blue-300'
              }`}>
                {diag.severity}
              </span>
            )}
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-sm text-gray-300 leading-relaxed">
            <div className="text-xs text-gray-500 mb-2">Chain-of-thought reasoning</div>
            {diag.reasoning}
          </div>
          <div className="flex gap-4 text-xs text-gray-500">
            {diag.confidence != null && (
              <span>Confidence: <span className="text-green-400 font-medium">{(diag.confidence * 100).toFixed(0)}%</span></span>
            )}
            <span>LLM invoked: <span className="text-gray-300">{diag.llm_invoked ? 'yes' : 'no — statistical path'}</span></span>
            <span>Prompt: <span className="text-gray-300">{diag.prompt_version}</span></span>
          </div>
        </div>
      </StageCard>

      {/* Stage 2: Librarian (shown when fault detected) */}
      {!isNoFault && lib.repair_steps && (
        <StageCard title="Stage 2 — Technical Librarian (Hybrid RAG)" icon={BookOpen} status="pass">
          <div className="space-y-4">
            <div className="flex gap-4 text-xs text-gray-500 flex-wrap">
              <span>Faithfulness: <span className="text-green-400 font-medium">{((lib.faithfulness_score ?? 0) * 100).toFixed(0)}%</span></span>
              <span>Chunks retrieved: <span className="text-gray-300">{lib.retrieval_count}</span></span>
              <span>Est. duration: <span className="text-gray-300">{lib.estimated_duration_minutes} min</span></span>
            </div>
            <div className="space-y-2">
              {(lib.repair_steps || []).map((step: { step: number; action: string; safety_critical: boolean }) => (
                <div key={step.step} className={`flex gap-3 p-2.5 rounded text-sm ${
                  step.safety_critical ? 'bg-amber-900/20 border border-amber-800/50' : 'bg-gray-800/50'
                }`}>
                  <span className="text-gray-500 w-5 shrink-0 pt-0.5">{step.step}.</span>
                  <span className="text-gray-200 leading-relaxed">{step.action}</span>
                  {step.safety_critical && <Shield className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" />}
                </div>
              ))}
            </div>
            {lib.parts_list?.length > 0 && (
              <div className="flex gap-2 flex-wrap mt-2">
                {lib.parts_list.map((p: { part_number: string; part_name: string; quantity: number }) => (
                  <span key={p.part_number} className="text-xs bg-blue-900/30 text-blue-300 border border-blue-800/50 px-2 py-1 rounded font-mono">
                    {p.part_number} × {p.quantity}
                    <span className="text-blue-500 ml-1 font-sans">{p.part_name}</span>
                  </span>
                ))}
              </div>
            )}
            {lib.parts_list?.length === 0 && (
              <div className="text-xs text-gray-500 mt-2">No parts required — facility escalation procedure.</div>
            )}
          </div>
        </StageCard>
      )}

      {/* Stage 3: Safety Auditor */}
      {!isNoFault && audit.decision && (
        <StageCard title="Stage 3 — Safety Auditor (Adversarial Gate)" icon={Shield}
          status={audit.decision === 'GO' ? 'pass' : audit.decision === 'GO_WITH_CONDITIONS' ? 'warn' : 'fail'}>
          <div className="space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <span className={`text-sm font-bold px-3 py-1 rounded ${
                audit.decision === 'GO' ? 'bg-green-900/50 text-green-300 border border-green-700' :
                audit.decision === 'GO_WITH_CONDITIONS' ? 'bg-amber-900/50 text-amber-300 border border-amber-700' :
                'bg-red-900/50 text-red-300 border border-red-700'
              }`}>
                {audit.decision?.replace('_', ' ')}
              </span>
              <span className="text-xs text-gray-400">
                V={audit.voltage_checked}V · {audit.arc_flash_rating}
                {audit.hard_rule_triggered && (
                  <span className="ml-2 text-red-400 font-medium">· Hard rule triggered</span>
                )}
              </span>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-sm text-gray-300 leading-relaxed">
              {audit.reason}
            </div>
            {audit.ppe_required && audit.decision !== 'NO_GO' && (
              <div className="text-xs text-amber-300 bg-amber-900/20 border border-amber-800/50 px-3 py-2 rounded">
                PPE Required: {audit.ppe_required}
              </div>
            )}
          </div>
        </StageCard>
      )}

      {/* Stage 4: Work Order */}
      {isDispatched && wo.work_order_id && (
        <StageCard title="Stage 4 — Work Order Generated" icon={Clock} status="pass">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-mono text-blue-300">{wo.work_order_id}</div>
              <div className="text-xs text-gray-500 mt-1">Dispatched to on-call technician — parts requisitioned</div>
            </div>
            <span className="text-xs bg-green-900/50 text-green-300 border border-green-700 px-3 py-1.5 rounded-full">
              DISPATCHED
            </span>
          </div>
        </StageCard>
      )}

      {/* Blocked outcome summary */}
      {isBlocked && (
        <div className="bg-red-900/20 border border-red-700/50 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <XCircle className="h-5 w-5 text-red-400" />
            <span className="font-semibold text-white">Incident Closed — Safety Gate Rejected Work Order</span>
          </div>
          <p className="text-sm text-gray-400">
            The Safety Auditor issued a NO_GO decision due to hard rule violation. No work order was created.
            The incident remains open pending facility electrical team resolution.
          </p>
        </div>
      )}
    </div>
  )
}
