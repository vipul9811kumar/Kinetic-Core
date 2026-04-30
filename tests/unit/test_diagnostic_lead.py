"""Unit tests for DiagnosticLeadAgent — statistical screening only (no LLM calls)."""

import pytest
from agents.diagnostic_lead.agent import DiagnosticLeadAgent


def make_reading(temp: float, flow: float, vibr: float, volt: float = 480.0, curr: float = 18.5) -> dict:
    return {
        "device_id": "KCX-NYC-0042",
        "readings": {
            "temperature_celsius": temp,
            "voltage_v": volt,
            "current_a": curr,
            "vibration_mm_s": vibr,
            "coolant_flow_lpm": flow,
            "ambient_temp_celsius": 22.0,
            "power_factor": 0.92,
            "rpm": 1750,
        },
    }


@pytest.fixture
def agent():
    return DiagnosticLeadAgent.__new__(DiagnosticLeadAgent)


class TestStatisticalScreening:
    def test_normal_data_no_anomaly(self, agent):
        window = [make_reading(42.0 + i * 0.01, 185.0, 1.2) for i in range(20)]
        trends = agent._compute_trends(window)
        screen = agent._statistical_screen(trends)
        assert not screen["invoke_llm"]
        assert screen["severity"] == "LOW"

    def test_thermal_runaway_triggers_llm(self, agent):
        window = [make_reading(42.0 + i * 0.5, 185.0 - i * 1.5, 1.2 + i * 0.05) for i in range(20)]
        trends = agent._compute_trends(window)
        screen = agent._statistical_screen(trends)
        assert screen["invoke_llm"]
        assert "rising_temp" in screen["anomalies"]
        assert "declining_flow" in screen["anomalies"]

    def test_low_voltage_triggers_high_severity(self, agent):
        window = [make_reading(42.0, 185.0, 1.2, volt=430.0) for _ in range(10)]
        trends = agent._compute_trends(window)
        screen = agent._statistical_screen(trends)
        assert screen["invoke_llm"]
        assert "low_voltage" in screen["anomalies"]
        assert screen["severity"] == "HIGH"

    def test_vibration_spike_triggers_alert(self, agent):
        window = [make_reading(42.0, 185.0, 1.2 + i * 0.25) for i in range(20)]
        trends = agent._compute_trends(window)
        screen = agent._statistical_screen(trends)
        assert screen["invoke_llm"]
        assert "rising_vibration" in screen["anomalies"]

    def test_short_window_returns_empty_trends(self, agent):
        window = [make_reading(42.0, 185.0, 1.2)]
        trends = agent._compute_trends(window)
        assert trends == {}

    def test_fault_code_extraction_from_trends(self, agent):
        window = [make_reading(42.0 + i * 0.8, 185.0 - i * 2.0, 1.2 + i * 0.08, curr=18.5 + i * 0.2) for i in range(30)]
        trends = agent._compute_trends(window)
        assert trends["temp_trend_per_sample"] > 0
        assert trends["flow_trend_per_sample"] < 0
        assert trends["current_trend_per_sample"] > 0
