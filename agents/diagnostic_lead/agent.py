"""
Diagnostic Lead Agent

Analyzes a window of telemetry readings, detects anomalies using both
statistical methods and GPT-4o reasoning, and produces a structured
fault classification with root cause hypothesis.

Design principle: Statistical pre-screening runs first (no LLM cost).
GPT-4o is only invoked when statistical signals cross anomaly threshold.
"""

import json
import logging
import os
import statistics
from datetime import datetime, timezone
from typing import Any

from openai import AsyncAzureOpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

# Azure uses a named deployment; direct OpenAI uses the model name.
DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT4O", "gpt-4o")

FAULT_SIGNATURES = {
    "KX-T2209-B": {
        "name": "Coolant Pump Seal Degradation — Thermal Escalation",
        "indicators": ["declining_flow", "rising_temp", "rising_current"],
    },
    "KX-V1103-A": {
        "name": "Pump Bearing Micro-Failure — Vibration Escalation",
        "indicators": ["rising_vibration", "rpm_instability"],
    },
    "KX-E4412-A": {
        "name": "Supply Voltage Sag — Motor Underperformance",
        "indicators": ["low_voltage", "rising_current", "low_power_factor"],
    },
    "KX-P3301-C": {
        "name": "Coolant Pressure Drop — Blockage",
        "indicators": ["declining_flow", "stable_or_normal_temp"],
    },
    "KX-F2208-B": {
        "name": "Coolant Flow Sensor Fault",
        "indicators": ["erratic_flow_readings"],
    },
    "KX-C5501-A": {
        "name": "Control Board Communication Fault",
        "indicators": ["missing_readings", "timestamp_gaps"],
    },
}


class DiagnosticLeadAgent:
    def __init__(self, client: AsyncAzureOpenAI | AsyncOpenAI):
        self.client = client

    def _compute_trends(self, window: list[dict]) -> dict:
        """Statistical pre-screening: compute trends across all telemetry channels."""
        if len(window) < 3:
            return {}

        def get_channel(channel: str) -> list[float]:
            return [r["readings"][channel] for r in window if channel in r.get("readings", {})]

        temps = get_channel("temperature_celsius")
        flows = get_channel("coolant_flow_lpm")
        vibs = get_channel("vibration_mm_s")
        voltages = get_channel("voltage_v")
        currents = get_channel("current_a")
        rpms = get_channel("rpm")
        pf = get_channel("power_factor")

        def trend(values: list[float]) -> float:
            if len(values) < 2:
                return 0.0
            n = len(values)
            xs = list(range(n))
            x_mean = statistics.mean(xs)
            y_mean = statistics.mean(values)
            num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
            den = sum((x - x_mean) ** 2 for x in xs)
            return num / den if den != 0 else 0.0

        def cv(values: list[float]) -> float:
            """Coefficient of variation — measures instability."""
            if not values or statistics.mean(values) == 0:
                return 0.0
            return statistics.stdev(values) / abs(statistics.mean(values))

        return {
            "temp_trend_per_sample": trend(temps),
            "flow_trend_per_sample": trend(flows),
            "vibration_trend_per_sample": trend(vibs),
            "voltage_mean": statistics.mean(voltages) if voltages else 480.0,
            "voltage_min": min(voltages) if voltages else 480.0,
            "current_trend_per_sample": trend(currents),
            "rpm_cv": cv(rpms),
            "power_factor_mean": statistics.mean(pf) if pf else 0.92,
            "latest_temp": temps[-1] if temps else 0.0,
            "latest_flow": flows[-1] if flows else 185.0,
            "latest_vibration": vibs[-1] if vibs else 0.0,
            "flow_pct_change": (flows[-1] - flows[0]) / flows[0] * 100 if flows and flows[0] != 0 else 0.0,
        }

    def _statistical_screen(self, trends: dict) -> dict:
        """Rule-based anomaly flag — determines whether to invoke GPT-4o."""
        anomalies = []
        severity = "LOW"

        if trends.get("temp_trend_per_sample", 0) > 0.15:
            anomalies.append("rising_temp")
        if trends.get("flow_trend_per_sample", 0) < -0.5 or trends.get("flow_pct_change", 0) < -5:
            anomalies.append("declining_flow")
        if trends.get("vibration_trend_per_sample", 0) > 0.02:
            anomalies.append("rising_vibration")
        if trends.get("latest_vibration", 0) > 4.5:
            anomalies.append("rising_vibration")
            severity = "HIGH"
        if trends.get("voltage_min", 480) < 440:
            anomalies.append("low_voltage")
            severity = "HIGH"
        if trends.get("current_trend_per_sample", 0) > 0.1:
            anomalies.append("rising_current")
        if trends.get("rpm_cv", 0) > 0.03:
            anomalies.append("rpm_instability")
        if trends.get("power_factor_mean", 0.92) < 0.85:
            anomalies.append("low_power_factor")
        if trends.get("latest_temp", 0) > 70:
            severity = "HIGH" if trends["latest_temp"] > 80 else "MEDIUM"

        if len(anomalies) >= 2 and severity == "LOW":
            severity = "MEDIUM"

        return {"anomalies": anomalies, "severity": severity, "invoke_llm": bool(anomalies)}

    async def analyze(self, telemetry_window: list[dict], incident_id: str) -> dict:
        started_at = datetime.now(timezone.utc)
        device_id = telemetry_window[-1]["device_id"] if telemetry_window else "UNKNOWN"

        trends = self._compute_trends(telemetry_window)
        screen = self._statistical_screen(trends)

        base_result = {
            "agent": "DiagnosticLead",
            "incident_id": incident_id,
            "device_id": device_id,
            "analyzed_at": started_at.isoformat(),
            "window_size": len(telemetry_window),
            "statistical_trends": trends,
            "statistical_anomalies": screen["anomalies"],
        }

        if not screen["invoke_llm"]:
            return {**base_result, "fault_code": None, "severity": "LOW", "root_cause": None,
                    "fault_description": "No anomalies detected", "confidence": 1.0, "llm_invoked": False}

        prompt = self._build_diagnostic_prompt(telemetry_window, trends, screen)
        response = await self.client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )

        try:
            llm_output = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            llm_output = {"fault_code": None, "severity": "MEDIUM", "root_cause": "Parse error", "confidence": 0.5}

        return {
            **base_result,
            "fault_code": llm_output.get("fault_code"),
            "fault_description": llm_output.get("fault_description", ""),
            "severity": llm_output.get("severity", screen["severity"]),
            "root_cause": llm_output.get("root_cause"),
            "confidence": llm_output.get("confidence", 0.0),
            "reasoning": llm_output.get("reasoning", ""),
            "llm_invoked": True,
            "prompt_version": "v1.2",
            "tokens_used": response.usage.total_tokens if response.usage else 0,
        }

    def _system_prompt(self) -> str:
        return (
            "You are the Diagnostic Lead agent for Kinetic-Core, an industrial AI reliability platform. "
            "You analyze time-series telemetry from critical cooling units and diagnose equipment faults. "
            "You have deep expertise in thermal-fluid systems, pump mechanics, and electrical power quality. "
            "Always respond with valid JSON matching the required schema. "
            "Be conservative: only assign HIGH severity if sensor readings clearly indicate imminent failure. "
            "Valid fault codes: KX-T2209-B, KX-V1103-A, KX-P3301-C, KX-E4412-A, KX-F2208-B, KX-C5501-A."
        )

    def _build_diagnostic_prompt(self, window: list[dict], trends: dict, screen: dict) -> str:
        latest = window[-1]["readings"]
        earliest = window[0]["readings"]
        return f"""Analyze the following telemetry from a Kinetic-Core Model X cooling unit.

TELEMETRY WINDOW SUMMARY:
- Window duration: {len(window)} samples
- Device: {window[-1]['device_id']}
- Earliest readings: temp={earliest['temperature_celsius']}°C, flow={earliest['coolant_flow_lpm']} LPM, vibration={earliest['vibration_mm_s']} mm/s
- Latest readings: temp={latest['temperature_celsius']}°C, flow={latest['coolant_flow_lpm']} LPM, vibration={latest['vibration_mm_s']} mm/s

STATISTICAL TRENDS:
- Temperature trend: {trends.get('temp_trend_per_sample', 0):.4f} °C/sample (POSITIVE = rising)
- Flow trend: {trends.get('flow_trend_per_sample', 0):.4f} LPM/sample (NEGATIVE = declining)
- Flow % change over window: {trends.get('flow_pct_change', 0):.1f}%
- Vibration trend: {trends.get('vibration_trend_per_sample', 0):.4f} mm/s/sample
- Voltage min: {trends.get('voltage_min', 480):.1f}V (threshold: <440V = fault)
- Current trend: {trends.get('current_trend_per_sample', 0):.4f} A/sample
- RPM coefficient of variation: {trends.get('rpm_cv', 0):.4f} (>0.03 = unstable)
- Power factor mean: {trends.get('power_factor_mean', 0.92):.3f}

STATISTICAL ANOMALY FLAGS: {', '.join(screen['anomalies']) or 'none'}

Diagnose the fault and respond with this JSON schema:
{{
  "fault_code": "<KX-XXXX-X or null if no fault>",
  "fault_description": "<human readable description>",
  "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "root_cause": "<specific mechanical or electrical root cause>",
  "confidence": <0.0-1.0>,
  "reasoning": "<chain-of-thought: what pattern led to this diagnosis>"
}}"""
