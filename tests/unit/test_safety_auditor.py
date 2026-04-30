"""Unit tests for SafetyAuditorAgent hard rules — no LLM calls needed."""

import pytest
from agents.safety_auditor.agent import SafetyAuditorAgent


@pytest.fixture
def auditor():
    return SafetyAuditorAgent.__new__(SafetyAuditorAgent)


SAFE_SEAL_PLAN = {
    "repair_steps": [
        {"step": 1, "action": "Apply LOTO and engage lockout", "safety_critical": True},
        {"step": 2, "action": "Replace pump seal P-2209 after zero energy verified", "safety_critical": True},
    ],
    "safety_prerequisites": ["LOTO engaged", "voltage < 480V verified"],
}

UNSAFE_SEAL_PLAN = {
    "repair_steps": [{"step": 1, "action": "Replace seal immediately", "safety_critical": True}],
    "safety_prerequisites": [],
}


class TestHardRules:
    def test_high_voltage_blocks_pump_work(self, auditor):
        readings = {"voltage_v": 492.0, "temperature_celsius": 45.0, "vibration_mm_s": 1.2}
        result = auditor._rule_based_gate(SAFE_SEAL_PLAN, readings)
        assert result is not None
        assert result["decision"] == "NO_GO"
        assert "voltage" in result["reason"].lower()
        assert result["blocking_rule"] == "max_voltage_for_hot_swap"

    def test_safe_voltage_allows_pump_work(self, auditor):
        readings = {"voltage_v": 470.0, "temperature_celsius": 45.0, "vibration_mm_s": 1.2}
        result = auditor._rule_based_gate(SAFE_SEAL_PLAN, readings)
        assert result is None  # no hard block

    def test_high_temperature_blocks_seal_work(self, auditor):
        readings = {"voltage_v": 460.0, "temperature_celsius": 85.0, "vibration_mm_s": 1.2}
        result = auditor._rule_based_gate(SAFE_SEAL_PLAN, readings)
        assert result is not None
        assert result["decision"] == "NO_GO"
        assert result["blocking_rule"] == "max_temp_for_seal_work"

    def test_exact_voltage_threshold_boundary(self, auditor):
        readings_at_limit = {"voltage_v": 480.0, "temperature_celsius": 45.0, "vibration_mm_s": 1.2}
        result = auditor._rule_based_gate(SAFE_SEAL_PLAN, readings_at_limit)
        assert result is None  # exactly 480V is allowed

        readings_over = {"voltage_v": 480.1, "temperature_celsius": 45.0, "vibration_mm_s": 1.2}
        result = auditor._rule_based_gate(SAFE_SEAL_PLAN, readings_over)
        assert result is not None
        assert result["decision"] == "NO_GO"

    def test_arc_flash_rating_low_voltage(self, auditor):
        rating = auditor._determine_arc_flash(420.0)
        assert "Class 1" in rating

    def test_arc_flash_rating_medium_voltage(self, auditor):
        rating = auditor._determine_arc_flash(465.0)
        assert "Class 2" in rating

    def test_arc_flash_rating_high_voltage(self, auditor):
        rating = auditor._determine_arc_flash(485.0)
        assert "STOP" in rating
