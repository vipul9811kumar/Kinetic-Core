"""Tests for the synthetic telemetry generator."""

import pytest
from data.synthetic.telemetry.generator import generate_stream, DEVICE_CONFIGS, FAULT_SCENARIOS


def test_normal_scenario_generates_readings():
    device = DEVICE_CONFIGS[0]
    readings = list(generate_stream(device, "normal", total_hours=0.5, interval_seconds=300))
    assert len(readings) == 6
    for r in readings:
        assert "readings" in r
        assert "fault_flags" in r
        assert r["device_id"] == device["device_id"]


def test_thermal_runaway_raises_flags_by_hour_6():
    device = DEVICE_CONFIGS[0]
    readings = list(generate_stream(device, "thermal_runaway", total_hours=8.0, interval_seconds=1800))
    late_readings = readings[-4:]  # last 2 hours
    assert any(r["readings"]["temperature_celsius"] > 75 for r in late_readings), \
        "Expected thermal warning in final hours of thermal_runaway scenario"


def test_all_scenarios_produce_valid_readings():
    device = DEVICE_CONFIGS[0]
    for scenario in FAULT_SCENARIOS:
        readings = list(generate_stream(device, scenario, total_hours=1.0, interval_seconds=1800))
        assert len(readings) >= 1
        reading = readings[0]
        assert 0 <= reading["readings"]["power_factor"] <= 1
        assert reading["readings"]["temperature_celsius"] >= -10
        assert reading["readings"]["voltage_v"] >= 0


def test_reading_schema_fields_present():
    device = DEVICE_CONFIGS[0]
    readings = list(generate_stream(device, "normal", total_hours=0.25, interval_seconds=900))
    r = readings[0]
    required_reading_fields = {
        "temperature_celsius", "voltage_v", "current_a",
        "vibration_mm_s", "coolant_flow_lpm", "ambient_temp_celsius",
        "power_factor", "rpm"
    }
    assert required_reading_fields.issubset(r["readings"].keys())
    assert r["metadata"]["model"] == "Kinetic-Core Model X"
