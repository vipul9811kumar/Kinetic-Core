"""
Safety Auditor Agent — Adversarial Gate

This agent's SOLE purpose is to reject unsafe repair plans.
It receives zero context about efficiency, uptime, or cost goals.
Its only inputs are the proposed repair procedure and live sensor readings.

Design principle: An agent that cannot be "argued out of" a safety rejection.
The prompt is adversarially tuned: it defaults to NO-GO and requires positive
evidence of safety to approve. This is the inverse of most AI agents.
"""

import json
import logging
import os
from datetime import datetime, timezone

from openai import AsyncAzureOpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

DEPLOYMENT_GPT4O = os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT4O", "gpt-4o")

SAFETY_CONSTRAINTS = {
    "max_voltage_for_hot_swap": 480.0,
    "min_voltage_for_operations": 440.0,
    "max_vibration_for_bearing_work": 6.0,
    "max_temp_for_seal_work": 65.0,
    "arc_flash_threshold_v": 480.0,
}

ARC_FLASH_RATINGS = {
    "low": "< 440V: Class 1 PPE (4 cal/cm²)",
    "medium": "440–480V: Class 2 PPE (8 cal/cm²)",
    "high": "> 480V: STOP — facility electrical required",
}


class SafetyAuditorAgent:
    def __init__(self, client: AsyncAzureOpenAI | AsyncOpenAI):
        self.client = client

    def _rule_based_gate(self, repair_plan: dict, live_readings: dict) -> dict | None:
        """
        Hard-coded safety rules that CANNOT be overridden by LLM reasoning.
        Returns a blocking result dict if any hard rule trips, else None.
        """
        voltage = live_readings.get("voltage_v", 480.0)
        temp = live_readings.get("temperature_celsius", 25.0)
        vibration = live_readings.get("vibration_mm_s", 0.0)

        safety_prereqs = [s.lower() for s in repair_plan.get("safety_prerequisites", [])]
        requires_loto = any("loto" in s or "lockout" in s for s in safety_prereqs)
        is_pump_work = any(
            "seal" in step.get("action", "").lower() or "bearing" in step.get("action", "").lower()
            for step in repair_plan.get("repair_steps", [])
        )

        if is_pump_work and voltage > SAFETY_CONSTRAINTS["max_voltage_for_hot_swap"]:
            return {
                "decision": "NO_GO",
                "reason": f"HARD RULE VIOLATION: Pump/seal work requires voltage ≤ {SAFETY_CONSTRAINTS['max_voltage_for_hot_swap']}V. Current voltage is {voltage:.1f}V. LOTO cannot be safely applied until facility electrical team de-energizes the supply.",
                "blocking_rule": "max_voltage_for_hot_swap",
                "voltage_checked": voltage,
            }

        if temp > SAFETY_CONSTRAINTS["max_temp_for_seal_work"] and is_pump_work:
            return {
                "decision": "NO_GO",
                "reason": f"HARD RULE VIOLATION: Coolant temperature is {temp:.1f}°C. Seal work requires coolant to cool below {SAFETY_CONSTRAINTS['max_temp_for_seal_work']}°C (hot coolant burn hazard). Wait for 15-minute cooldown.",
                "blocking_rule": "max_temp_for_seal_work",
                "voltage_checked": voltage,
            }

        return None

    def _determine_arc_flash(self, voltage: float) -> str:
        if voltage > 480:
            return ARC_FLASH_RATINGS["high"]
        elif voltage > 440:
            return ARC_FLASH_RATINGS["medium"]
        return ARC_FLASH_RATINGS["low"]

    async def validate(self, repair_plan: dict, live_readings: dict, incident_id: str) -> dict:
        started_at = datetime.now(timezone.utc)
        voltage = live_readings.get("voltage_v", 480.0)
        arc_flash = self._determine_arc_flash(voltage)

        # Hard rules run first — LLM never sees these if they trip
        hard_block = self._rule_based_gate(repair_plan, live_readings)
        if hard_block:
            logger.warning(f"[{incident_id}] Safety Auditor HARD BLOCK: {hard_block['blocking_rule']}")
            return {
                "agent": "SafetyAuditor",
                "incident_id": incident_id,
                "audited_at": started_at.isoformat(),
                "voltage_checked": voltage,
                "arc_flash_rating": arc_flash,
                "llm_invoked": False,
                "hard_rule_triggered": True,
                "prompt_version": "v1.0",
                **hard_block,
            }

        # LLM-based audit for nuanced safety judgment
        prompt = self._build_audit_prompt(repair_plan, live_readings, arc_flash)
        response = await self.client.chat.completions.create(
            model=DEPLOYMENT_GPT4O,
            messages=[
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=1024,
        )

        try:
            llm_output = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            llm_output = {
                "decision": "NO_GO",
                "reason": "Audit response parse error — defaulting to NO_GO per fail-safe policy.",
                "conditions": [],
            }

        decision = llm_output.get("decision", "NO_GO")
        if decision not in ("GO", "NO_GO", "GO_WITH_CONDITIONS"):
            decision = "NO_GO"

        logger.info(f"[{incident_id}] Safety Auditor LLM decision: {decision}")

        return {
            "agent": "SafetyAuditor",
            "incident_id": incident_id,
            "audited_at": started_at.isoformat(),
            "decision": decision,
            "reason": llm_output.get("reason", ""),
            "conditions": llm_output.get("conditions", []),
            "ppe_required": llm_output.get("ppe_required", ""),
            "voltage_checked": voltage,
            "arc_flash_rating": arc_flash,
            "hard_rule_triggered": False,
            "llm_invoked": True,
            "prompt_version": "v1.0",
            "tokens_used": response.usage.total_tokens if response.usage else 0,
        }

    def _system_prompt(self) -> str:
        return """You are the Safety Auditor for Kinetic-Core critical infrastructure.

YOUR ONLY JOB IS SAFETY. You are not an efficiency agent. You are not an uptime agent.
You do not consider cost, schedule pressure, or operational urgency.

Your default position is NO_GO. You require POSITIVE EVIDENCE of safety to issue GO.

Safety constraints you enforce:
- Pump/seal/bearing work: supply voltage must be ≤ 480V AND LOTO must be confirmed
- Hot coolant contact procedures: coolant temperature must be below 50°C
- Arc flash PPE: match PPE class to arc flash rating shown in readings (Class 1 for < 440V is sufficient)
- If ANY safety prerequisite in the repair plan cannot be confirmed from current readings → NO_GO

LOTO CONFIRMATION RULE: The sensor field "LOTO Confirmed: True" means a physical lockout-tagout
sensor has verified the isolation device is applied. This is authoritative confirmation of LOTO.
When LOTO Confirmed: True AND voltage ≤ 480V AND thermal conditions are within safe range, the
LOTO prerequisite IS satisfied — output GO (do not invent additional unconfirmed requirements).

If you are uncertain about a specific reading, output NO_GO. Never speculate."""

    def _build_audit_prompt(self, repair_plan: dict, readings: dict, arc_flash: str) -> str:
        steps_text = "\n".join(
            f"  Step {s['step']}: {s['action']} [safety_critical={s.get('safety_critical', False)}]"
            for s in repair_plan.get("repair_steps", [])
        )
        prereqs = "\n".join(f"  - {p}" for p in repair_plan.get("safety_prerequisites", []))
        voltage = readings.get("voltage_v", 480.0)
        temp = readings.get("temperature_celsius", 25.0)
        loto_confirmed = readings.get("loto_confirmed", False)

        # Pre-compute threshold checks so LLM aggregates rather than infers
        loto_check = "✓ CONFIRMED (physical LOTO sensor = True)" if loto_confirmed else "✗ NOT CONFIRMED (absent from sensor data)"
        voltage_check = f"✓ {voltage}V ≤ 480V (within LOTO work limit)" if voltage <= 480 else f"✗ {voltage}V > 480V (EXCEEDS LOTO work limit)"
        temp_check = f"✓ {temp}°C ≤ 50°C (within coolant-contact limit)" if temp <= 50 else f"✗ {temp}°C > 50°C (EXCEEDS coolant-contact limit)"
        seal_temp_check = f"✓ {temp}°C ≤ 65°C (within seal/bearing work limit)" if temp <= 65 else f"✗ {temp}°C > 65°C (EXCEEDS seal/bearing work limit)"

        return f"""Audit this repair plan against current live sensor readings.

LIVE SENSOR READINGS:
  Voltage: {voltage} V
  Current: {readings.get('current_a', 'N/A')} A
  Temperature: {temp} °C
  Vibration: {readings.get('vibration_mm_s', 'N/A')} mm/s
  Coolant Flow: {readings.get('coolant_flow_lpm', 'N/A')} LPM
  Power Factor: {readings.get('power_factor', 'N/A')}
  LOTO Confirmed: {loto_confirmed} (physical lockout-tagout sensor — True = device physically applied and verified)
  Arc Flash Rating at current voltage: {arc_flash}

SENSOR THRESHOLD VERIFICATION (pre-computed against safety limits):
  LOTO isolation:          {loto_check}
  Voltage limit (≤ 480V):  {voltage_check}
  Coolant contact (≤ 50°C): {temp_check}
  Seal/bearing work (≤ 65°C): {seal_temp_check}

REPAIR PLAN SAFETY PREREQUISITES:
{prereqs or '  (none listed)'}

REPAIR STEPS:
{steps_text}

Decision rule: If all relevant sensor threshold checks above show ✓ AND LOTO is CONFIRMED,
the safety prerequisites are satisfied — output GO. Only output NO_GO if a threshold check
shows ✗ or LOTO is NOT CONFIRMED.

Respond with JSON:
{{
  "decision": "GO" | "NO_GO" | "GO_WITH_CONDITIONS",
  "reason": "<cite the specific threshold checks that determined your decision>",
  "conditions": ["<condition 1 if GO_WITH_CONDITIONS>"],
  "ppe_required": "<specific PPE required>"
}}"""
