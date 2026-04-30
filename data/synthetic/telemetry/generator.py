"""
Synthetic IoT telemetry generator for Kinetic-Core cooling units.

Fleet: 12 devices across 5 data center facilities (NYC, CHI, DFW, LAX, SEA).
Each device has unique baseline values and a pre-assigned fault scenario so
the generated dataset represents a realistic mixed-state fleet.

Usage:
    python generator.py --scenario thermal_runaway --hours 8 --output data/
    python generator.py --all-devices --all-scenarios --hours 24 --output data/
    python generator.py --stream  # publishes to Azure IoT Hub
"""

import argparse
import json
import math
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import numpy as np

# ── Fleet definition ─────────────────────────────────────────────────────────
# 12 devices across 5 facilities. baseline_overrides customise per-unit values
# so the fleet shows natural variation (older units run hotter, newer are cooler).

DEVICE_CONFIGS = [
    # FAC-NYC-DC-01 — New York  (4 units)
    {
        "device_id": "KCX-NYC-0042", "facility_id": "FAC-NYC-DC-01", "rack_id": "RACK-B7-U12",
        "model": "KX-CPS-5000", "install_date": "2022-06-15", "last_service_date": "2025-12-10",
        "assigned_scenario": "thermal_runaway",
        "baseline_overrides": {"temperature_celsius": 43.5, "current_a": 19.1},
    },
    {
        "device_id": "KCX-NYC-0043", "facility_id": "FAC-NYC-DC-01", "rack_id": "RACK-B7-U14",
        "model": "KX-CPS-5000", "install_date": "2022-06-15", "last_service_date": "2025-12-10",
        "assigned_scenario": "normal",
        "baseline_overrides": {},
    },
    {
        "device_id": "KCX-NYC-0044", "facility_id": "FAC-NYC-DC-01", "rack_id": "RACK-C2-U01",
        "model": "KX-CPS-5000", "install_date": "2023-01-10", "last_service_date": "2026-01-08",
        "assigned_scenario": "vibration_bearing",
        "baseline_overrides": {"vibration_mm_s": 1.4, "rpm": 1740},
    },
    {
        "device_id": "KCX-NYC-0045", "facility_id": "FAC-NYC-DC-01", "rack_id": "RACK-C2-U03",
        "model": "KX-CPS-5000", "install_date": "2023-01-10", "last_service_date": "2026-01-08",
        "assigned_scenario": "voltage_sag",
        "baseline_overrides": {"voltage_v": 478.0},
    },
    # FAC-CHI-DC-02 — Chicago  (3 units)
    {
        "device_id": "KCX-CHI-0011", "facility_id": "FAC-CHI-DC-02", "rack_id": "RACK-A3-U08",
        "model": "KX-CPS-5000", "install_date": "2022-09-20", "last_service_date": "2025-11-20",
        "assigned_scenario": "vibration_bearing",
        "baseline_overrides": {"temperature_celsius": 41.0, "ambient_temp_celsius": 21.0},
    },
    {
        "device_id": "KCX-CHI-0012", "facility_id": "FAC-CHI-DC-02", "rack_id": "RACK-A3-U10",
        "model": "KX-CPS-5000", "install_date": "2022-09-20", "last_service_date": "2026-02-14",
        "assigned_scenario": "sensor_fault",
        "baseline_overrides": {},
    },
    {
        "device_id": "KCX-CHI-0013", "facility_id": "FAC-CHI-DC-02", "rack_id": "RACK-D1-U02",
        "model": "KX-CPS-5000", "install_date": "2023-03-15", "last_service_date": "2026-02-14",
        "assigned_scenario": "normal",
        "baseline_overrides": {"current_a": 18.2, "power_factor": 0.91},
    },
    # FAC-DFW-DC-03 — Dallas  (2 units)
    {
        "device_id": "KCX-DFW-0008", "facility_id": "FAC-DFW-DC-03", "rack_id": "RACK-F2-U05",
        "model": "KX-CPS-5000", "install_date": "2021-11-30", "last_service_date": "2025-10-15",
        "assigned_scenario": "voltage_sag",
        "baseline_overrides": {"temperature_celsius": 44.0, "vibration_mm_s": 1.3},
    },
    {
        "device_id": "KCX-DFW-0009", "facility_id": "FAC-DFW-DC-03", "rack_id": "RACK-F2-U07",
        "model": "KX-CPS-5000", "install_date": "2021-11-30", "last_service_date": "2025-10-15",
        "assigned_scenario": "pressure_drop",
        "baseline_overrides": {"coolant_flow_lpm": 188.0},
    },
    # FAC-LAX-DC-04 — Los Angeles  (2 units, new facility)
    {
        "device_id": "KCX-LAX-0001", "facility_id": "FAC-LAX-DC-04", "rack_id": "RACK-A1-U04",
        "model": "KX-CPS-5000", "install_date": "2024-02-01", "last_service_date": "2026-02-01",
        "assigned_scenario": "normal",
        "baseline_overrides": {"ambient_temp_celsius": 24.0},
    },
    {
        "device_id": "KCX-LAX-0002", "facility_id": "FAC-LAX-DC-04", "rack_id": "RACK-A1-U06",
        "model": "KX-CPS-5000", "install_date": "2024-02-01", "last_service_date": "2026-03-15",
        "assigned_scenario": "thermal_runaway",
        "baseline_overrides": {"ambient_temp_celsius": 24.0, "temperature_celsius": 43.0},
    },
    # FAC-SEA-DC-05 — Seattle  (1 unit, new facility)
    {
        "device_id": "KCX-SEA-0001", "facility_id": "FAC-SEA-DC-05", "rack_id": "RACK-B3-U01",
        "model": "KX-CPS-5000", "install_date": "2024-06-15", "last_service_date": "2026-03-20",
        "assigned_scenario": "normal",
        "baseline_overrides": {"ambient_temp_celsius": 20.0, "temperature_celsius": 41.5},
    },
]

# ── Fault scenarios ───────────────────────────────────────────────────────────

FAULT_SCENARIOS = {
    "thermal_runaway": {
        "description": "Pump seal degradation — coolant flow reduction causes non-linear thermal escalation",
        "fault_code": "KX-T2209-B",
        "onset_hour": 2,
        "peak_hour": 6,
        "degradation_rate": 0.013,
    },
    "vibration_bearing": {
        "description": "Bearing micro-failure — progressive vibration increase with RPM instability",
        "fault_code": "KX-V1103-A",
        "onset_hour": 1,
        "peak_hour": 8,
        "degradation_rate": 0.008,
    },
    "voltage_sag": {
        "description": "Facility supply voltage sag — motor underperformance and power quality degradation",
        "fault_code": "KX-E4412-A",
        "onset_hour": 3,
        "peak_hour": 5,
        "degradation_rate": 0.02,
    },
    "pressure_drop": {
        "description": "Strainer blockage causing coolant flow restriction — temperature stable (not seal failure)",
        "fault_code": "KX-P3301-C",
        "onset_hour": 4,
        "peak_hour": 9,
        "degradation_rate": 0.015,
    },
    "sensor_fault": {
        "description": "Flow sensor calibration drift — erratic readings, other sensors unaffected",
        "fault_code": "KX-F2208-B",
        "onset_hour": 0,
        "peak_hour": 6,
        "degradation_rate": 0.025,
    },
    "normal": {
        "description": "Normal operating conditions with minor natural variance",
        "fault_code": None,
        "onset_hour": None,
        "peak_hour": None,
        "degradation_rate": 0.0,
    },
}

# ── Fleet-wide baseline (per-device overrides applied on top) ─────────────────

BASELINES = {
    "temperature_celsius": 42.0,
    "voltage_v": 480.0,
    "current_a": 18.5,
    "vibration_mm_s": 1.2,
    "coolant_flow_lpm": 185.0,
    "ambient_temp_celsius": 22.0,
    "power_factor": 0.92,
    "rpm": 1750,
}

# ── Noise levels per sensor ───────────────────────────────────────────────────

NOISE = {
    "temperature_celsius": 0.3,
    "voltage_v": 2.0,
    "current_a": 0.15,
    "vibration_mm_s": 0.05,
    "coolant_flow_lpm": 1.5,
    "ambient_temp_celsius": 0.2,
    "power_factor": 0.005,
    "rpm": 10,
}


def _noise(scale: float = 1.0) -> float:
    return random.gauss(0, scale)


def _sigmoid_degradation(hour: float, onset: float, peak: float) -> float:
    """Sigmoid curve from 0→1 between onset and peak."""
    if hour < onset:
        return 0.0
    x = (hour - onset) / (peak - onset + 1e-9)
    return 1 / (1 + math.exp(-8 * (x - 0.5)))


def generate_reading(
    device_config: dict,
    timestamp: datetime,
    scenario: str,
    elapsed_hours: float,
) -> dict:
    sc = FAULT_SCENARIOS[scenario]

    # Start from fleet baseline, then apply per-device overrides
    b = {**BASELINES, **device_config.get("baseline_overrides", {})}

    deg = 0.0
    if sc["onset_hour"] is not None:
        deg = _sigmoid_degradation(elapsed_hours, sc["onset_hour"], sc["peak_hour"])

    # ── Apply fault physics ───────────────────────────────────────────────────
    if scenario == "thermal_runaway":
        b["coolant_flow_lpm"] *= (1 - deg * 0.35)
        b["temperature_celsius"] += deg * 45.0 + elapsed_hours * 0.4
        b["vibration_mm_s"] += deg * 2.8
        b["current_a"] += deg * 4.2
        b["rpm"] = int(b["rpm"] * (1 - deg * 0.12))

    elif scenario == "vibration_bearing":
        b["vibration_mm_s"] += deg * 8.5 + elapsed_hours * 0.15
        b["temperature_celsius"] += deg * 8.0
        b["rpm"] = int(b["rpm"] * (1 - deg * 0.06))

    elif scenario == "voltage_sag":
        b["voltage_v"] *= (1 - deg * 0.18)
        b["current_a"] *= (1 + deg * 0.22)
        b["power_factor"] -= deg * 0.12
        b["temperature_celsius"] += deg * 6.0

    elif scenario == "pressure_drop":
        # Flow drops but temperature stays relatively stable — distinguishes blockage from seal failure
        b["coolant_flow_lpm"] *= (1 - deg * 0.30)
        b["temperature_celsius"] += deg * 9.0
        b["current_a"] += deg * 1.8
        # No significant vibration or RPM change

    elif scenario == "sensor_fault":
        # Flow sensor produces erratic readings — other sensors stable
        sensor_noise_amplifier = 1.0 + deg * 12.0
        b["coolant_flow_lpm"] += _noise(NOISE["coolant_flow_lpm"] * sensor_noise_amplifier)

    # ── Add Gaussian noise ────────────────────────────────────────────────────
    readings = {
        "temperature_celsius": round(b["temperature_celsius"] + _noise(NOISE["temperature_celsius"]), 2),
        "voltage_v": round(b["voltage_v"] + _noise(NOISE["voltage_v"]), 1),
        "current_a": round(b["current_a"] + _noise(NOISE["current_a"]), 2),
        "vibration_mm_s": round(max(0.1, b["vibration_mm_s"] + _noise(NOISE["vibration_mm_s"])), 3),
        "coolant_flow_lpm": round(max(0.0, b["coolant_flow_lpm"] + _noise(NOISE["coolant_flow_lpm"])), 1),
        "ambient_temp_celsius": round(b["ambient_temp_celsius"] + _noise(NOISE["ambient_temp_celsius"]), 1),
        "power_factor": round(min(1.0, max(0.0, b["power_factor"] + _noise(NOISE["power_factor"]))), 3),
        "rpm": max(0, int(b["rpm"]) + int(_noise(NOISE["rpm"]))),
    }

    # ── Fault flags derived from thresholds ───────────────────────────────────
    fault_flags = {
        "thermal_warning": readings["temperature_celsius"] > 75.0,
        "flow_deviation": readings["coolant_flow_lpm"] < b["coolant_flow_lpm"] * 0.85,
        "vibration_alert": readings["vibration_mm_s"] > 4.5,
        "voltage_anomaly": readings["voltage_v"] < 440.0 or readings["voltage_v"] > 510.0,
    }

    return {
        "device_id": device_config["device_id"],
        "facility_id": device_config["facility_id"],
        "rack_id": device_config["rack_id"],
        "timestamp": timestamp.isoformat(),
        "readings": readings,
        "fault_flags": fault_flags,
        "metadata": {
            "firmware_version": "3.2.1",
            "model": device_config.get("model", "KX-CPS-5000"),
            "install_date": device_config.get("install_date", "2023-01-01"),
            "last_service_date": device_config.get("last_service_date"),
        },
    }


def generate_stream(
    device_config: dict,
    scenario: str,
    total_hours: float = 8.0,
    interval_seconds: int = 30,
    start_time: datetime | None = None,
) -> Iterator[dict]:
    if start_time is None:
        start_time = datetime.now(timezone.utc) - timedelta(hours=total_hours)

    total_points = int(total_hours * 3600 / interval_seconds)
    for i in range(total_points):
        elapsed_hours = i * interval_seconds / 3600.0
        ts = start_time + timedelta(seconds=i * interval_seconds)
        yield generate_reading(device_config, ts, scenario, elapsed_hours)


def save_to_jsonl(
    scenario: str,
    total_hours: float,
    output_dir: Path,
    device_config: dict | None = None,
) -> Path:
    if device_config is None:
        device_config = DEVICE_CONFIGS[0]

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"{scenario}_{device_config['device_id']}_{total_hours}h.jsonl"

    count = 0
    with open(filename, "w") as f:
        for reading in generate_stream(device_config, scenario, total_hours):
            f.write(json.dumps(reading) + "\n")
            count += 1

    print(f"Generated {count} telemetry points → {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description="Kinetic-Core synthetic telemetry generator — 12-device fleet")
    parser.add_argument("--scenario", choices=list(FAULT_SCENARIOS.keys()), default="thermal_runaway")
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--output", type=str, default="data/synthetic/telemetry/output")
    parser.add_argument("--all-devices", action="store_true", help="Generate for all 12 devices (uses assigned_scenario)")
    parser.add_argument("--all-scenarios", action="store_true", help="Generate all fault scenarios for first device")
    args = parser.parse_args()

    output_dir = Path(args.output)

    if args.all_devices:
        total = 0
        for device in DEVICE_CONFIGS:
            scenario = device["assigned_scenario"]
            save_to_jsonl(scenario, args.hours, output_dir, device)
            total += 1
        print(f"\nGenerated telemetry for all {total} devices using their assigned scenarios.")
    elif args.all_scenarios:
        for scenario in FAULT_SCENARIOS:
            save_to_jsonl(scenario, args.hours, output_dir, DEVICE_CONFIGS[0])
    else:
        save_to_jsonl(args.scenario, args.hours, output_dir, DEVICE_CONFIGS[0])

    print("Done. Use ingestion/iot_simulator/simulator.py to publish to IoT Hub.")


if __name__ == "__main__":
    main()
