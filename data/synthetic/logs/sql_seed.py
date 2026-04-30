"""
Seed script for the maintenance log database.

Creates 500 realistic historical maintenance records across all 12 devices and
all 6 fault types. Includes three deliberate mis-diagnoses at indices 47, 183,
and 361 to demonstrate the AI's self-correction over prompt versions.

Usage:
    python sql_seed.py --count 500 --export-csv data/synthetic/logs/output
    python sql_seed.py --db sqlite:///data/synthetic/logs/maintenance.db
"""

import argparse
import csv
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from sqlalchemy import Column, DateTime, Float, Integer, String, Boolean, Text, create_engine
    from sqlalchemy.orm import DeclarativeBase, Session
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

FAULT_CATALOG = [
    {
        "code": "KX-T2209-B",
        "name": "Coolant Pump Seal Degradation — Thermal Escalation",
        "severity": "HIGH",
        "avg_resolution_min": 42,
        "repair_actions": [
            "Isolate unit from power supply (verify LOTO)",
            "Allow 15-minute coolant cool-down (below 50°C)",
            "Drain coolant loop to service reservoir",
            "Remove pump assembly cover (4x M8 bolts, torque 24 Nm cross-pattern)",
            "Inspect seal housing for wear patterns (Manual §5.1)",
            "Replace shaft seal P-2209 and O-ring set P-3301",
            "Refill coolant with Kinetic-Core Type-III fluid",
            "Pressure test at 120 PSI for 10 minutes (accept < 2 PSI loss)",
            "Restore power and verify flow ≥ 175 LPM within 3 minutes",
        ],
        "parts": [
            {"part_number": "P-2209", "part_name": "Coolant Pump Shaft Seal", "quantity": 1},
            {"part_number": "P-3301", "part_name": "O-Ring Set (12-piece)", "quantity": 1},
        ],
    },
    {
        "code": "KX-V1103-A",
        "name": "Pump Bearing Micro-Failure — Vibration Escalation",
        "severity": "MEDIUM",
        "avg_resolution_min": 65,
        "repair_actions": [
            "Schedule maintenance window (unit can operate at reduced capacity for 48h)",
            "Verify voltage < 480V before bearing access",
            "Remove motor end-cap (8x M6 bolts — note 2 bolts at 3 & 9 o'clock are 65mm, not 45mm)",
            "Extract bearing using P-1103-PULLER tool",
            "Install pre-lubricated replacement bearing P-1103-SKF",
            "Re-torque end-cap M6 bolts to 12 Nm",
            "Verify vibration ≤ 1.5 mm/s and RPM 1750 ±25 post-repair",
        ],
        "parts": [
            {"part_number": "P-1103-SKF", "part_name": "Deep Groove Ball Bearing 6204-2RS", "quantity": 2},
        ],
    },
    {
        "code": "KX-P3301-C",
        "name": "Coolant Pressure Drop — Strainer Blockage",
        "severity": "MEDIUM",
        "avg_resolution_min": 28,
        "repair_actions": [
            "Run high-velocity flush at 120% pump speed for 5 minutes",
            "Inspect and clean strainer screen P-STR-001 (M32 fitting access)",
            "Replace strainer if > 30% blocked",
            "Check expansion tank level and refill to MID mark",
            "Verify all valve positions per Manual §5.1 schematic",
            "Monitor flow rate for 30 minutes post-flush (target ≥ 175 LPM)",
        ],
        "parts": [
            {"part_number": "P-STR-001", "part_name": "Coolant Strainer Screen (50-micron)", "quantity": 1},
        ],
    },
    {
        "code": "KX-E4412-A",
        "name": "Supply Voltage Sag — Motor Underperformance",
        "severity": "HIGH",
        "avg_resolution_min": 18,
        "repair_actions": [
            "Contact facility electrical team — DO NOT perform PDU repairs onsite",
            "Log voltage readings every 15 minutes",
            "If voltage < 420V, execute graceful shutdown (Manual §8.2)",
            "Coordinate with UPS bypass if sustained sag > 30 minutes",
        ],
        "parts": [],
    },
    {
        "code": "KX-F2208-B",
        "name": "Coolant Flow Sensor Fault — Calibration Drift",
        "severity": "LOW",
        "avg_resolution_min": 22,
        "repair_actions": [
            "Verify sensor wiring harness connections at J-14 connector",
            "Check sensor P-2208 calibration against inline reference flow meter",
            "Clean sensor ultrasonic transducer faces with isopropyl alcohol",
            "Replace sensor P-2208 if calibration deviation > 5%",
        ],
        "parts": [
            {"part_number": "P-2208", "part_name": "Ultrasonic Flow Sensor", "quantity": 1},
        ],
    },
    {
        "code": "KX-C5501-A",
        "name": "Control Board Communication Fault",
        "severity": "LOW",
        "avg_resolution_min": 35,
        "repair_actions": [
            "Power cycle control board (hold RST button for 5 seconds)",
            "Check CAN bus termination resistors (must be 120Ω at each network end)",
            "Update firmware if version < 3.2.1 (see release notes)",
            "Replace control board P-CB-5501 if fault persists after firmware update",
        ],
        "parts": [
            {"part_number": "P-CB-5501", "part_name": "Primary Control Board Assembly", "quantity": 1},
        ],
    },
]

TECHNICIANS = [
    {"id": "TECH-001", "name": "Maria Santos"},
    {"id": "TECH-002", "name": "James Okafor"},
    {"id": "TECH-003", "name": "Lin Wei"},
    {"id": "TECH-004", "name": "David Petrov"},
    {"id": "TECH-005", "name": "Aisha Mohammed"},
    {"id": "TECH-006", "name": "Carlos Rivera"},
]

DEVICES = [
    {"device_id": "KCX-NYC-0042", "facility_id": "FAC-NYC-DC-01"},
    {"device_id": "KCX-NYC-0043", "facility_id": "FAC-NYC-DC-01"},
    {"device_id": "KCX-NYC-0044", "facility_id": "FAC-NYC-DC-01"},
    {"device_id": "KCX-NYC-0045", "facility_id": "FAC-NYC-DC-01"},
    {"device_id": "KCX-CHI-0011", "facility_id": "FAC-CHI-DC-02"},
    {"device_id": "KCX-CHI-0012", "facility_id": "FAC-CHI-DC-02"},
    {"device_id": "KCX-CHI-0013", "facility_id": "FAC-CHI-DC-02"},
    {"device_id": "KCX-DFW-0008", "facility_id": "FAC-DFW-DC-03"},
    {"device_id": "KCX-DFW-0009", "facility_id": "FAC-DFW-DC-03"},
    {"device_id": "KCX-LAX-0001", "facility_id": "FAC-LAX-DC-04"},
    {"device_id": "KCX-LAX-0002", "facility_id": "FAC-LAX-DC-04"},
    {"device_id": "KCX-SEA-0001", "facility_id": "FAC-SEA-DC-05"},
]

# Misdiagnosis records: index → (wrong_code, correct_code, note)
MISDIAGNOSES = {
    47: (
        "KX-E4412-A",
        "KX-V1103-A",
        "Initial AI diagnosis suggested KX-E4412-A (voltage). Confirmed as KX-V1103-A (bearing) after manual inspection. Prompt v0.9 false positive — corrected in v1.0.",
    ),
    183: (
        "KX-T2209-B",
        "KX-P3301-C",
        "AI flagged thermal signature consistent with seal failure. Root cause confirmed as strainer blockage — flow/temp ratio mismatch was key discriminator. Added to diagnostic training set.",
    ),
    361: (
        "KX-F2208-B",
        "KX-T2209-B",
        "Erratic flow readings initially attributed to sensor drift. Actual cause was early-stage seal degradation. Prompt v1.1 update introduced flow/temperature correlation check to prevent recurrence.",
    ),
}


def _random_past_datetime(days_back: int = 730) -> datetime:
    offset = timedelta(days=random.uniform(0, days_back), hours=random.uniform(0, 24))
    return datetime.now(timezone.utc) - offset


def generate_log_entry(index: int) -> dict:
    misdiag = MISDIAGNOSES.get(index)

    if misdiag:
        wrong_code, correct_code, note = misdiag
        fault = next(f for f in FAULT_CATALOG if f["code"] == correct_code)
        ai_match = False
    else:
        fault = random.choice(FAULT_CATALOG)
        ai_match = True
        note = ""

    device = random.choice(DEVICES)
    tech = random.choice(TECHNICIANS)
    reported_at = _random_past_datetime(730)

    noise = random.gauss(1.0, 0.18)
    resolution_minutes = max(10, int(fault["avg_resolution_min"] * noise))
    resolved_at = reported_at + timedelta(minutes=resolution_minutes)

    log_id_date = reported_at.strftime("%Y%m%d")
    log_id = f"LOG-{log_id_date}-{index:04d}"
    incident_id = f"INC-{reported_at.year}-{index:04d}"

    return {
        "log_id": log_id,
        "device_id": device["device_id"],
        "facility_id": device["facility_id"],
        "incident_id": incident_id,
        "fault_code": fault["code"],
        "fault_description": fault["name"],
        "severity": fault["severity"],
        "reported_at": reported_at.isoformat(),
        "resolved_at": resolved_at.isoformat(),
        "resolution_minutes": resolution_minutes,
        "technician_id": tech["id"],
        "technician_name": tech["name"],
        "repair_actions": fault["repair_actions"],
        "parts_replaced": fault["parts"],
        "outcome": random.choices(
            ["RESOLVED", "ESCALATED", "DEFERRED"],
            weights=[0.85, 0.10, 0.05],
        )[0],
        "root_cause_confirmed": fault["name"],
        "ai_diagnosis_match": ai_match,
        "notes": note,
    }


def generate_all_records(count: int = 500) -> list[dict]:
    return [generate_log_entry(i + 1) for i in range(count)]


def export_csv(records: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    flat_records = []
    for r in records:
        flat = {k: v for k, v in r.items() if not isinstance(v, (list, dict))}
        flat["repair_actions"] = " | ".join(r["repair_actions"])
        flat["parts_replaced"] = json.dumps(r["parts_replaced"])
        flat_records.append(flat)

    out_path = output_dir / "maintenance_logs.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=flat_records[0].keys())
        writer.writeheader()
        writer.writerows(flat_records)
    print(f"Exported {len(flat_records)} records → {out_path}")

    jsonl_path = output_dir / "maintenance_logs.jsonl"
    with open(jsonl_path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"Exported {len(records)} records → {jsonl_path}")


def main():
    parser = argparse.ArgumentParser(description="Seed 500 maintenance log records across 12 devices and 6 technicians")
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--export-csv", type=str, default="data/synthetic/logs/output")
    parser.add_argument("--db", type=str, default=None, help="SQLAlchemy DB URL (optional)")
    args = parser.parse_args()

    records = generate_all_records(args.count)
    export_csv(records, Path(args.export_csv))

    if args.db:
        if not HAS_SQLALCHEMY:
            print("Install sqlalchemy to use --db: pip install sqlalchemy")
            return
        print(f"DB export to {args.db} — implement with SQLAlchemy ORM models as needed.")

    print(f"\nGenerated {len(records)} records across {len(DEVICES)} devices and {len(TECHNICIANS)} technicians.")
    print(f"Deliberate misdiagnoses: records {sorted(MISDIAGNOSES.keys())} (for evaluation harness).")


if __name__ == "__main__":
    main()
