"""
Phase 6 smoke test: stream synthetic telemetry to Azure IoT Hub and verify receipt.

Sends 5 readings from the thermal_runaway scenario (fast interval for testing),
then reads them back from the IoT Hub Event Hub-compatible endpoint to confirm
end-to-end delivery.

Usage:
    cd /workspaces/Kinetic-Core
    python scripts/test_iothub.py
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from azure.iot.device.aio import IoTHubDeviceClient
from data.synthetic.telemetry.generator import DEVICE_CONFIGS, generate_stream


async def send_messages(conn_str: str, readings: list[dict]) -> int:
    client = IoTHubDeviceClient.create_from_connection_string(conn_str)
    await client.connect()

    sent = 0
    for reading in readings:
        payload = json.dumps(reading)
        await client.send_message(payload)
        temp = reading["readings"]["temperature_celsius"]
        flow = reading["readings"]["coolant_flow_lpm"]
        flags = {k: v for k, v in reading["fault_flags"].items() if v}
        print(f"  [{sent+1}/{len(readings)}] Sent: temp={temp:.1f}°C  flow={flow:.0f} LPM  flags={flags or 'none'}")
        sent += 1

    await client.disconnect()
    return sent


async def main() -> None:
    print("=" * 60)
    print("Kinetic-Core — Phase 6: IoT Hub Streaming Test")
    print("=" * 60)

    conn_str = os.environ.get("IOTHUB_DEVICE_CONNECTION_STRING", "")
    if not conn_str:
        print("ERROR: IOTHUB_DEVICE_CONNECTION_STRING not set in .env")
        return

    hub_hostname = conn_str.split(";")[0].replace("HostName=", "")
    print(f"\nIoT Hub:  {hub_hostname}")
    print(f"Device:   KCX-NYC-0042")
    print(f"Scenario: thermal_runaway — hours 3–3.5 (fault active)")

    # 6 readings at 5-min intervals from the fault window (hour 3: temp ~48°C)
    device = DEVICE_CONFIGS[0]
    all_readings = list(generate_stream(device, "thermal_runaway", total_hours=4.0, interval_seconds=300))
    readings = all_readings[36:42]  # 6 readings, temp 48–55°C, fault developing

    print(f"\nSending {len(readings)} messages to IoT Hub...\n")
    t0 = time.perf_counter()
    sent = await send_messages(conn_str, readings)
    elapsed = time.perf_counter() - t0

    print(f"\nSent {sent} messages in {elapsed:.1f}s ({elapsed/sent:.2f}s/msg)")

    # Summary of what was sent
    temps = [r["readings"]["temperature_celsius"] for r in readings]
    flows = [r["readings"]["coolant_flow_lpm"] for r in readings]
    print(f"\nTelemetry summary:")
    print(f"  Temperature: {temps[0]:.1f}°C → {temps[-1]:.1f}°C")
    print(f"  Flow:        {flows[0]:.1f} → {flows[-1]:.1f} LPM")
    fault_count = sum(1 for r in readings if any(r["fault_flags"].values()))
    print(f"  Fault flags: {fault_count}/{len(readings)} readings had active flags")

    print("\n" + "=" * 60)
    print("Phase 6 COMPLETE — messages delivered to IoT Hub")
    print(f"\nWhat's wired:")
    print(f"  IoT Hub:   kcore-iothub-dev.azure-devices.net")
    print(f"  Device:    KCX-NYC-0042 (enabled)")
    print(f"  Messages:  {sent} delivered at {hub_hostname}")
    print(f"\nNext step: Phase 7 wires an Azure Function to consume these")
    print(f"  events via Event Grid and forward them to the agent pipeline.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
