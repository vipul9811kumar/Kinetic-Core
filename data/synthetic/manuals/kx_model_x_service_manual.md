# KINETIC-CORE MODEL X — TECHNICAL SERVICE MANUAL

**Document ID:** KCX-TSM-2024-REV3  
**Model:** Kinetic-Core Model X High-Density Cooling Unit  
**Revision:** 3.1 (2024-09-01)  
**Classification:** Technical — Authorized Service Personnel Only

---

## Table of Contents

1. Safety Precautions and Arc Flash Requirements
2. Unit Overview and Specifications
3. Fault Code Taxonomy
4. Diagnostic Procedures
5. Repair Procedures by Fault Code
6. Preventive Maintenance Schedule
7. Spare Parts Catalog
8. Wiring Diagrams and Schematics
9. Troubleshooting Decision Tree
10. Contact and Escalation

---

## Chapter 1: Safety Precautions and Arc Flash Requirements

### 1.1 Mandatory Pre-Work Safety Checks

**WARNING:** Failure to follow lockout/tagout (LOTO) procedures may result in severe injury or death. All work on live electrical components requires PPE rated for the arc flash boundary.

Before beginning ANY maintenance procedure on a Kinetic-Core Model X unit:

1. **Verify voltage level at supply terminal.** Normal operating range: 460–480V AC, 3-phase.
   - If voltage exceeds **480V**: DO NOT PROCEED. Contact facility electrical team immediately.
   - If voltage is between **460–480V**: Proceed with Class 2 arc flash PPE (minimum 8 cal/cm²).
   - If voltage is below **440V**: Log the event as fault KX-E4412-A before proceeding.

2. **Engage LOTO:** Apply lockout to all energy sources at the unit disconnect switch. Verify zero energy state with calibrated voltage tester.

3. **PPE Requirements by Task:**

| Task | Required PPE |
|---|---|
| Visual inspection (unit running) | Safety glasses, class 0 gloves |
| Sensor replacement | Safety glasses, class 0 gloves, LOTO |
| Pump/bearing replacement | Safety glasses, class 2 arc flash suit, LOTO |
| Control board replacement | Safety glasses, class 0 gloves, ESD wrist strap, LOTO |
| Full pump assembly R&R | Safety glasses, class 2 arc flash suit, LOTO, chemical splash goggles |

### 1.2 Coolant Safety

The Kinetic-Core Type-III coolant fluid is a propylene glycol-based solution. Do not mix with Type-I or Type-II fluid variants. Maintain SDS (Safety Data Sheet) on-site. Coolant disposal must comply with local environmental regulations.

**Hot Coolant Hazard:** After running, coolant temperature can exceed 90°C. Allow 15-minute cooldown before breaking coolant connections. Wear chemical splash goggles and insulated gloves.

---

## Chapter 2: Unit Overview and Specifications

### 2.1 Model X Performance Specifications

| Parameter | Specification | Critical Threshold |
|---|---|---|
| Cooling Capacity | 50 kW rated | N/A |
| Supply Voltage | 480V AC, 3-phase | < 440V or > 510V: fault KX-E4412-A |
| Coolant Flow Rate | 185 LPM nominal | < 150 LPM: fault KX-T2209-B suspected |
| Max Coolant Temperature | 65°C inlet | > 75°C: thermal warning |
| Pump Motor RPM | 1,750 RPM nominal | < 1,500 RPM: performance warning |
| Vibration Limit | 2.0 mm/s RMS | > 4.5 mm/s: fault KX-V1103-A suspected |
| Power Factor | 0.92 nominal | < 0.85: investigate motor load |

### 2.2 Component Map

```
[FRONT PANEL]
├── Display Panel (status LEDs + LCD)
├── Emergency Stop (red, mushroom)
└── Service Access Panel (2x quarter-turn fasteners)

[INTERNAL — LEFT SIDE]
├── Control Board Assembly (P-CB-5501)
│   ├── CAN Bus Interface (J-14 connector)
│   └── Firmware update port (USB-C, internal)
├── Flow Sensor (P-2208) — inline, pre-pump
└── Supply Terminal Block (3-phase + neutral + ground)

[INTERNAL — RIGHT SIDE]
├── Pump Motor Assembly
│   ├── Bearing Housing (front bearing: P-1103-SKF)
│   ├── Shaft Seal Assembly (P-2209)
│   ├── O-Ring Set (P-3301) — 12-piece kit
│   └── Coolant Pump Head
├── Heat Exchanger (brazed plate, 40-circuit)
├── Expansion Tank
└── Pressure Relief Valve (factory-set 175 PSI, DO NOT ADJUST)
```

---

## Chapter 3: Fault Code Taxonomy

### Complete Fault Code Reference

| Code | Name | Severity | Typical Root Cause | Auto-Recovery |
|---|---|---|---|---|
| **KX-T2209-B** | Coolant Pump Seal Degradation — Thermal Escalation | HIGH | Pump shaft seal wear from age or chemical incompatibility | No |
| **KX-V1103-A** | Pump Bearing Micro-Failure — Vibration Escalation | MEDIUM | Bearing fatigue, lubrication failure, or contamination | No |
| **KX-P3301-C** | Coolant Pressure Drop — Blockage | MEDIUM | Strainer screen blockage, air ingestion, or valve misposition | Partial |
| **KX-E4412-A** | Supply Voltage Sag — Motor Underperformance | HIGH | Facility power quality event, PDU fault, or wiring issue | No (facility action) |
| **KX-F2208-B** | Coolant Flow Sensor Fault | LOW | Sensor drift, wiring fault, or fouled ultrasonic transducer | No |
| **KX-C5501-A** | Control Board Communication Fault | LOW | Firmware crash, CAN bus termination fault, EMI | Yes (power cycle) |

### Early Warning Signatures (Pre-Fault)

The following telemetry patterns typically precede fault codes by 2–6 hours. The Kinetic-Core AI monitoring system (where deployed) uses these as predictive indicators:

**Preceding KX-T2209-B:**
- Coolant flow rate declining > 5% over any 3-hour window
- Temperature rising > 0.5°C/hour with no change in ambient temperature
- Current draw increasing > 2% with no load change (pump working harder against reduced flow)

**Preceding KX-V1103-A:**
- Vibration RMS increasing > 0.1 mm/s/day
- Slight RPM instability (±30 RPM variation from baseline)
- Minor temperature increase at bearing housing (+3–5°C)

---

## Chapter 4: Diagnostic Procedures

### 4.1 Systematic Fault Isolation — Thermal Events

When a thermal warning is displayed (temperature > 75°C), follow this decision tree:

**Step 1: Check Flow Rate**
- If flow < 150 LPM → Suspect KX-T2209-B (seal) or KX-P3301-C (blockage)
- If flow ≥ 150 LPM → Check ambient temperature and rack heat load

**Step 2: If Flow is Low — Distinguish Seal vs. Blockage**
- Check pump inlet pressure (use P-GAUGE-001 at service port):
  - High inlet pressure, low outlet flow → Blockage (KX-P3301-C)
  - Low inlet pressure, normal outlet resistance → Seal degradation (KX-T2209-B)
- Listen for pump cavitation sounds (gurgling, not humming)
  - Cavitation present → Likely air ingestion or blockage

**Step 3: Check Vibration**
- Vibration > 2.5 mm/s alongside thermal event → Co-occurring KX-V1103-A
- Document both fault codes if bearing failure is co-occurring with thermal event

### 4.2 Diagnostic Data Collection Requirements

Before calling the Technical Support Center (TSC), collect:
1. Full telemetry export for the 6 hours preceding fault onset
2. Visual photos of pump assembly and seal area
3. Current firmware version (display: Settings → System Info)
4. Facility power quality log for the preceding 24 hours

---

## Chapter 5: Repair Procedures by Fault Code

### 5.1 KX-T2209-B — Coolant Pump Seal Replacement

**Tools Required:** Torque wrench (5–50 Nm range), M8 socket set, seal puller P-PULL-2209, coolant catch basin (minimum 10L)

**Estimated Duration:** 35–50 minutes  
**Recommended Team Size:** 2 technicians

**CRITICAL SAFETY GATE:** This procedure requires the supply voltage to be < 480V AND the LOTO to be in place before beginning. If voltage exceeds 480V at any point during LOTO verification, STOP and contact facility electrical.

**Procedure:**

1. **Isolate and LOTO** — Engage lockout at unit disconnect switch. Verify zero energy state at three supply terminals (L1, L2, L3) with calibrated tester. Tag the lockout device with technician ID.

2. **Cool-down wait** — If unit was running, wait minimum 15 minutes for coolant temperature to drop below 50°C. Check temperature at service port thermometer.

3. **Drain coolant** — Connect drain hose to service drain valve (bottom-right of pump assembly). Open valve and drain to catch basin. Volume: approximately 8 liters. Close valve when flow stops.

4. **Access pump assembly** — Remove service access panel (2x quarter-turn fasteners). Remove pump cover plate (4x M8 bolts, 24 Nm torque). Set aside bolts in order — they are different lengths.

5. **Remove seal assembly** — Using P-PULL-2209 puller tool, extract the shaft seal from the pump housing. Note orientation of the seal before removal (white face toward pump impeller). Inspect shaft surface for scoring — if shaft is scored >0.2mm deep, escalate to KCX Level 2 repair.

6. **Clean seal bore** — Wipe seal bore with lint-free cloth and isopropyl alcohol. Inspect O-ring groove for debris or damage.

7. **Install new seal P-2209** — Lubricate new seal lip with clean Type-III coolant (do not use petroleum-based lubricant). Press seal into bore by hand to seat, then use seal driver P-DRV-2209 to fully seat. Seat depth: flush with bore face ±0.5mm.

8. **Install new O-ring set P-3301** — Replace all 12 O-rings in the kit. Lubricate each with clean coolant before installation. Ensure O-rings are seated fully in grooves without twisting.

9. **Reassemble pump cover** — Torque M8 bolts to 24 Nm in cross-pattern sequence. Torque sequence: top-left, bottom-right, top-right, bottom-left.

10. **Refill coolant** — Add Kinetic-Core Type-III coolant to expansion tank until level reaches MAX line. Do not overfill.

11. **Pressure test** — Connect P-PUMP-TEST pressure tester to service port. Pressurize system to 120 PSI. Hold 10 minutes. Acceptable pressure loss: < 2 PSI in 10 minutes. If loss > 2 PSI, re-inspect all O-ring seats.

12. **Remove LOTO and restore power** — Remove lockout, restore power. Monitor flow rate display for 5 minutes. Expected: flow rate ≥ 175 LPM within 3 minutes of startup.

13. **Verify and log** — Confirm temperature trending downward within 10 minutes. Log repair in maintenance system with parts used: P-2209 (qty 1), P-3301 (qty 1). Clear fault code KX-T2209-B from control panel.

---

### 5.2 KX-V1103-A — Pump Bearing Replacement

**Tools Required:** Torque wrench, M6 socket set (6 Nm, 12 Nm), bearing puller P-BEAR-1103, brass mallet, bearing driver set

**Estimated Duration:** 55–75 minutes  
**Recommended Team Size:** 2 technicians

**CRITICAL SAFETY GATE:** Verify voltage < 480V. This procedure allows a 48-hour deferral window — schedule during the next planned maintenance window if uptime constraints apply.

**Procedure:**

1. Complete LOTO per §5.1 Steps 1–2.

2. **Remove motor end-cap** — Remove 8x M6 bolts (12 Nm torque). Note: 2 bolts at positions 3 and 9 o'clock are longer (65mm vs. 45mm standard). Mark their positions.

3. **Extract front bearing** — Use bearing puller P-BEAR-1103. Pull evenly — do not use heat. Place old bearing in labeled bag for records.

4. **Inspect shaft journal** — Check shaft diameter with micrometer at bearing journal. Nominal: 30.000mm. Replace shaft if diameter < 29.985mm.

5. **Install new bearing P-1103-SKF** — Bearing is pre-lubricated; do not add additional grease. Press using bearing driver to ensure full seat against shoulder. Bearing should be flush with housing face.

6. **Reassemble end-cap** — Torque M6 bolts to 12 Nm in star pattern.

7. **Restore power and verify** — Monitor vibration reading for 15 minutes. Expected: vibration ≤ 1.5 mm/s. RPM should stabilize at 1,750 ±25 RPM.

---

### 5.3 KX-P3301-C — Coolant System Flush

**Estimated Duration:** 20–35 minutes. This is the only procedure that may be performed with the unit running (flow flush step only). Full LOTO required for strainer replacement.

**Procedure:**

1. **High-velocity flush** — Set unit to manual override mode (hold MODE + ▲ for 3 seconds). Select "FLUSH CYCLE." Unit will run pump at 120% speed for 5 minutes, dislodging minor blockages.

2. **Check strainer** — If flush does not restore flow to > 160 LPM, LOTO required. Access strainer P-STR-001 at service port (single M32 fitting). Remove, inspect mesh — replace if > 30% blocked.

3. **Check all valves** — Refer to §8.2 valve position schematic. All isolation valves should be fully open (handle parallel to pipe).

4. **Inspect expansion tank** — Level between MIN and MAX. If below MIN, air may have entered system. Perform air purge: open bleed valve at heat exchanger top (1/4 turn, 30 seconds, close).

---

## Chapter 6: Preventive Maintenance Schedule

| Task | Interval | Reference |
|---|---|---|
| Visual inspection — all fittings and connections | Weekly | §4.1 |
| Verify flow rate against baseline | Monthly | §2.1 |
| Strainer inspection and cleaning (P-STR-001) | Quarterly | §5.3 |
| Full bearing vibration check with vibration analyzer | Semi-annual | §4.2 |
| Shaft seal inspection (P-2209) | Annual | §5.1 |
| Full coolant sample analysis (chemistry check) | Annual | Lab kit KCX-TEST-001 |
| Firmware update to latest release | As released | §2.2 |

---

## Chapter 7: Spare Parts Catalog

| Part Number | Description | Unit | MTBR |
|---|---|---|---|
| P-2209 | Coolant Pump Shaft Seal | Each | 3–5 years |
| P-3301 | O-Ring Set (12-piece kit for pump assembly) | Kit | With P-2209 |
| P-1103-SKF | Deep Groove Ball Bearing 6204-2RS | Each | 5–7 years |
| P-STR-001 | Coolant Strainer Screen (mesh 50 micron) | Each | 1–3 years |
| P-2208 | Ultrasonic Flow Sensor | Each | 7–10 years |
| P-CB-5501 | Primary Control Board | Each | 10+ years |
| P-3303-FILT | Coolant Filter Cartridge | Each | 6 months |

---

## Chapter 8: Contact and Escalation

| Level | Condition | Contact |
|---|---|---|
| Level 1 | Any fault code with repair procedure in Chapter 5 | On-site technician |
| Level 2 | Shaft scoring > 0.2mm, structural damage, multiple concurrent faults | KCX Technical Support: 1-800-KCX-TECH |
| Level 3 | Unit replacement, warranty claim, repeated fault recurrence | KCX Field Service: fieldservice@kineticcore.io |

**Emergency hotline (24/7):** +1-800-KCX-EMRG

---

*End of Kinetic-Core Model X Technical Service Manual Rev 3.1*  
*Document ID: KCX-TSM-2024-REV3 — For technical support, scan QR code on unit chassis.*
