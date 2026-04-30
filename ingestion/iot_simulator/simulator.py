"""
IoT Hub Simulator

Publishes synthetic telemetry to Azure IoT Hub using the MQTT device SDK.
Reads pre-generated JSONL files from the telemetry generator OR streams
live-generated data at configurable intervals.

Usage:
    # Stream live thermal_runaway scenario to IoT Hub
    python simulator.py --scenario thermal_runaway --device KCX-NYC-0042 --live

    # Replay a recorded JSONL file
    python simulator.py --file data/synthetic/telemetry/output/thermal_runaway_KCX-NYC-0042_8h.jsonl

    # Dry run (print to stdout, no IoT Hub)
    python simulator.py --scenario normal --dry-run --hours 2
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def _publish_to_iothub(device_id: str, payload: dict, conn_str: str) -> None:
    try:
        from azure.iot.device.aio import IoTHubDeviceClient

        client = IoTHubDeviceClient.create_from_connection_string(conn_str)
        await client.connect()
        message_str = json.dumps(payload)
        await client.send_message(message_str)
        await client.disconnect()
    except ImportError:
        logger.error("Install azure-iot-device: pip install azure-iot-device")
        raise


async def stream_live(
    scenario: str,
    device_config: dict,
    interval_seconds: int,
    dry_run: bool,
    hours: float,
    conn_str: str | None,
) -> None:
    sys.path.insert(0, str(Path(__file__).parents[2]))
    from data.synthetic.telemetry.generator import generate_stream

    logger.info(f"Starting live stream: scenario={scenario}, device={device_config['device_id']}, interval={interval_seconds}s")
    count = 0

    for reading in generate_stream(device_config, scenario, total_hours=hours, interval_seconds=interval_seconds):
        if dry_run:
            print(json.dumps(reading))
        else:
            await _publish_to_iothub(device_config["device_id"], reading, conn_str)
            logger.info(
                f"Published: temp={reading['readings']['temperature_celsius']}°C "
                f"flow={reading['readings']['coolant_flow_lpm']} LPM "
                f"flags={reading['fault_flags']}"
            )
        count += 1
        await asyncio.sleep(interval_seconds)

    logger.info(f"Stream complete: {count} messages published")


async def replay_file(filepath: Path, dry_run: bool, conn_str: str | None, speed: float = 1.0) -> None:
    logger.info(f"Replaying file: {filepath} at {speed}x speed")
    with open(filepath) as f:
        lines = f.readlines()

    logger.info(f"Replaying {len(lines)} records")
    for i, line in enumerate(lines):
        reading = json.loads(line.strip())
        if dry_run:
            print(json.dumps(reading))
        else:
            await _publish_to_iothub(reading["device_id"], reading, conn_str)
            logger.info(f"[{i+1}/{len(lines)}] Published {reading['device_id']} @ {reading['timestamp']}")
        await asyncio.sleep(0.1 / speed)

    logger.info("Replay complete")


def main():
    parser = argparse.ArgumentParser(description="Kinetic-Core IoT Hub Simulator")
    parser.add_argument("--scenario", choices=["thermal_runaway", "vibration_bearing", "voltage_sag", "normal"],
                        default="thermal_runaway")
    parser.add_argument("--device", default="KCX-NYC-0042", help="Device ID to simulate")
    parser.add_argument("--file", type=str, help="Replay a JSONL file instead of live generation")
    parser.add_argument("--live", action="store_true", help="Stream live to IoT Hub")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout only (no IoT Hub)")
    parser.add_argument("--hours", type=float, default=8.0, help="Hours of data to generate (live mode)")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between messages (live mode)")
    parser.add_argument("--speed", type=float, default=1.0, help="Replay speed multiplier")
    args = parser.parse_args()

    conn_str = os.environ.get("IOTHUB_DEVICE_CONNECTION_STRING")
    if not args.dry_run and not conn_str:
        logger.error("Set IOTHUB_DEVICE_CONNECTION_STRING or use --dry-run")
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).parents[2]))
    from data.synthetic.telemetry.generator import DEVICE_CONFIGS

    device_config = next((d for d in DEVICE_CONFIGS if d["device_id"] == args.device), DEVICE_CONFIGS[0])

    if args.file:
        asyncio.run(replay_file(Path(args.file), args.dry_run, conn_str, args.speed))
    else:
        asyncio.run(stream_live(args.scenario, device_config, args.interval, args.dry_run, args.hours, conn_str))


if __name__ == "__main__":
    main()
