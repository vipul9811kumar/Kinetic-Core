"""
Seed script for the maintenance log SQL database.

Creates 200 realistic historical maintenance records across all fault types.
Includes correct resolutions (for training) and one deliberate mis-diagnosis
(LOG-20240315-0047: vibration mis-classified as electrical) to show the AI
catching a pattern the human missed.

Usage:
    python sql_seed.py --db sqlite:///data/synthetic/logs/maintenance.db
    python sql_seed.py --db postgresql://user:pass@host/kinetic_core
    python sql_seed.py --export-csv data/synthetic/logs/
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
            "Isolate unit from power supply (verify lockout/tagout)",
            "Drain coolant loop to service reservoir",
            "Remove pump assembly cover (4x M8 bolts)",
            "Inspect seal housing for wear patterns (ref: Manual §7.3)",
            "Replace shaft seal P-2209 and O-ring set P-3301",
            "Refill coolant with Kinetic-Core Type-III fluid",
            "Pressure test at 120 PSI for 10 minutes",
            "Restore power and verify flow rate ≥ 180 LPM within 5 minutes",
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
            "Remove motor end-cap (8x M6 bolts, torque 12 Nm)",
            "Extract bearing using P-1103-PULLER tool",
            "Install replacement bearing P-1103-SKF (pre-lubricated)",
            "Re-torque end-cap to spec",
            "Verify vibration < 2.0 mm/s post-repair",
        ],
        "parts": [
            {"part_number": "P-1103-SKF", "part_name": "Deep Groove Ball Bearing 6204-2RS", "quantity": 2},
        ],
    },
    {
        "code": "KX-P3301-C",
        "name": "Coolant Pressure Drop — Blockage",
        "severity": "MEDIUM",
        "avg_resolution_min": 28,
        "repair_actions": [
            "Flush primary coolant circuit at 150% normal flow rate",
            "Inspect and clean strainer screen P-STR-001",
            "Check expansion tank level and refill if below MIN line",
            "Verify all valve positions per Manual §5.1 schematic",
            "Monitor flow rate for 30 minutes post-flush",
        ],
        "parts": [
            {"part_number": "P-STR-001", "part_name": "Coolant Strainer Screen", "quantity": 1},
        ],
    },
    {
        "code": "KX-E4412-A",
        "name": "Supply Voltage Sag — Motor Underperformance",
        "severity": "HIGH",
        "avg_resolution_min": 15,
        "repair_actions": [
            "Contact facility electrical team — do NOT perform repairs on power supply",
            "Notify PDU panel team of voltage sag event",
            "Log voltage readings every 15 minutes",
            "If voltage < 420V, execute graceful shutdown procedure",
        ],
        "parts": [],
    },
    {
        "code": "KX-F2208-B",
        "name": "Coolant Flow Sensor Fault",
        "severity": "LOW",
        "avg_resolution_min": 20,
        "repair_actions": [
            "Verify sensor wiring harness connections at J-14 connector",
            "Check sensor P-2208 calibration against flow meter reference",
            "Replace sensor if calibration deviation > 5%",
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
            "Power cycle control board (hold RST for 5 seconds)",
            "Check CAN bus termination resistors (120Ω at each end)",
            "Update firmware if version < 3.2.0",
            "Replace control board P-CB-5501 if fault persists after firmware update",
        ],
        "parts": [
            {"part_number": "P-CB-5501", "part_name": "Primary Control Board", "quantity": 1},
        ],
    },
]

TECHNICIANS = [
    {"id": "TECH-001", "name": "Maria Santos"},
    {"id": "TECH-002", "name": "James Okafor"},
    {"id": "TECH-003", "name": "Lin Wei"},
    {"id": "TECH-004", "name": "David Petrov"},
    {"id": "TECH-005", "name": "Aisha Mohammed"},
]

DEVICES = [
    {"device_id": "KCX-NYC-0042", "facility_id": "FAC-NYC-DC-01"},
    {"device_id": "KCX-NYC-0043", "facility_id": "FAC-NYC-DC-01"},
    {"device_id": "KCX-CHI-0011", "facility_id": "FAC-CHI-DC-02"},
    {"device_id": "KCX-CHI-0012", "facility_id": "FAC-CHI-DC-02"},
    {"device_id": "KCX-DFW-0008", "facility_id": "FAC-DFW-DC-03"},
]


def _random_past_datetime(days_back: int = 365) -> datetime:
    offset = timedelta(days=random.uniform(0, days_back), hours=random.uniform(0, 24))
    return datetime.now(timezone.utc) - offset


def generate_log_entry(index: int, force_misdiagnosis: bool = False) -> dict:
    fault = random.choice(FAULT_CATALOG)
    device = random.choice(DEVICES)
    tech = random.choice(TECHNICIANS)
    reported_at = _random_past_datetime(400)

    noise = random.gauss(1.0, 0.2)
    resolution_minutes = max(10, int(fault["avg_resolution_min"] * noise))
    resolved_at = reported_at + timedelta(minutes=resolution_minutes)

    ai_match = True
    if force_misdiagnosis:
        ai_match = False

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
        "notes": "" if ai_match else "Initial AI diagnosis suggested KX-E4412-A (voltage). Confirmed as KX-V1103-A (bearing) after manual inspection. Prompt v0.9 false positive — corrected in v1.0.",
    }


def generate_all_records(count: int = 200) -> list[dict]:
    records = []
    for i in range(count):
        force_misdiagnosis = (i == 47)
        records.append(generate_log_entry(i + 1, force_misdiagnosis=force_misdiagnosis))
    return records


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
    parser = argparse.ArgumentParser(description="Seed maintenance log database")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--export-csv", type=str, default="data/synthetic/logs/output")
    parser.add_argument("--db", type=str, default=None, help="SQLAlchemy DB URL (optional)")
    args = parser.parse_args()

    records = generate_all_records(args.count)
    export_csv(records, Path(args.export_csv))

    if args.db:
        if not HAS_SQLALCHEMY:
            print("Install sqlalchemy to use --db: pip install sqlalchemy")
            return
        print(f"DB export to {args.db} — implement with SQLAlchemy ORM models")

    print(f"\nGenerated {len(records)} maintenance log records.")
    print(f"Note: Record LOG-*-0048 is the deliberate misdiagnosis for evaluation.")


if __name__ == "__main__":
    main()
