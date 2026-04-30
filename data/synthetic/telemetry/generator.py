"""
Synthetic IoT telemetry generator for Kinetic-Core Model X cooling units.

Generates realistic time-series data with a "hidden fault" baked in:
a gradual coolant pump seal degradation that causes non-linear temperature
rise — detectable by AI pattern analysis but missed by simple thresholds.

Usage:
    python generator.py --scenario thermal_runaway --hours 8 --output data/
    python generator.py --scenario normal --hours 24 --output data/
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

DEVICE_CONFIGS = [
    {"device_id": "KCX-NYC-0042", "facility_id": "FAC-NYC-DC-01", "rack_id": "RACK-B7-U12"},
    {"device_id": "KCX-NYC-0043", "facility_id": "FAC-NYC-DC-01", "rack_id": "RACK-B7-U14"},
    {"device_id": "KCX-CHI-0011", "facility_id": "FAC-CHI-DC-02", "rack_id": "RACK-A3-U08"},
]

FAULT_SCENARIOS = {
    "thermal_runaway": {
        "description": "Pump seal degradation causing coolant flow reduction and thermal escalation",
        "fault_code": "KX-T2209-B",
        "onset_hour": 2,
        "peak_hour": 6,
        "degradation_rate": 0.013,
    },
    "vibration_bearing": {
        "description": "Bearing micro-failure causing progressive vibration increase",
        "fault_code": "KX-V1103-A",
        "onset_hour": 1,
        "peak_hour": 8,
        "degradation_rate": 0.008,
    },
    "voltage_sag": {
        "description": "Supply voltage sag causing motor performance degradation",
        "fault_code": "KX-E4412-A",
        "onset_hour": 3,
        "peak_hour": 5,
        "degradation_rate": 0.02,
    },
    "normal": {
        "description": "Normal operating conditions with minor natural variance",
        "fault_code": None,
        "onset_hour": None,
        "peak_hour": None,
        "degradation_rate": 0.0,
    },
}

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


def _noise(scale: float = 1.0) -> float:
    return random.gauss(0, scale)


def _sigmoid_degradation(hour: float, onset: float, peak: float, rate: float) -> float:
    """Returns a 0→1 degradation factor using a sigmoid curve."""
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
    b = BASELINES.copy()

    deg = 0.0
    if sc["onset_hour"] is not None:
        deg = _sigmoid_degradation(
            elapsed_hours,
            sc["onset_hour"],
            sc["peak_hour"],
            sc["degradation_rate"],
        )

    if scenario == "thermal_runaway":
        flow_drop = deg * 0.35
        b["coolant_flow_lpm"] *= (1 - flow_drop)
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

    readings = {
        "temperature_celsius": round(b["temperature_celsius"] + _noise(0.3), 2),
        "voltage_v": round(b["voltage_v"] + _noise(2.0), 1),
        "current_a": round(b["current_a"] + _noise(0.15), 2),
        "vibration_mm_s": round(max(0.1, b["vibration_mm_s"] + _noise(0.05)), 3),
        "coolant_flow_lpm": round(max(0.0, b["coolant_flow_lpm"] + _noise(1.5)), 1),
        "ambient_temp_celsius": round(b["ambient_temp_celsius"] + _noise(0.2), 1),
        "power_factor": round(min(1.0, max(0.0, b["power_factor"] + _noise(0.005))), 3),
        "rpm": max(0, b["rpm"] + int(_noise(10))),
    }

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
            "model": "Kinetic-Core Model X",
            "install_date": "2023-03-15",
            "last_service_date": "2024-11-20",
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
    parser = argparse.ArgumentParser(description="Kinetic-Core synthetic telemetry generator")
    parser.add_argument("--scenario", choices=list(FAULT_SCENARIOS.keys()), default="thermal_runaway")
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--output", type=str, default="data/synthetic/telemetry/output")
    parser.add_argument("--all-devices", action="store_true", help="Generate for all device configs")
    parser.add_argument("--all-scenarios", action="store_true", help="Generate all scenarios")
    args = parser.parse_args()

    output_dir = Path(args.output)
    scenarios = list(FAULT_SCENARIOS.keys()) if args.all_scenarios else [args.scenario]
    devices = DEVICE_CONFIGS if args.all_devices else [DEVICE_CONFIGS[0]]

    for scenario in scenarios:
        for device in devices:
            save_to_jsonl(scenario, args.hours, output_dir, device)

    print("Done. Use this data with ingestion/iot_simulator/simulator.py to publish to IoT Hub.")


if __name__ == "__main__":
    main()
