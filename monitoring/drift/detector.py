"""
Model Drift Detector

Weekly batch job that compares current diagnostic agent accuracy against
the golden evaluation set. If F1 score drops > 5% from baseline, fires
an alert and optionally triggers retraining.

Run via:
    - Azure Data Factory weekly trigger
    - GitHub Actions scheduled workflow (cron: '0 6 * * MON')
    - Local: python detector.py --evaluate
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASELINE_F1 = float(os.environ.get("BASELINE_F1_SCORE", "0.91"))
DRIFT_THRESHOLD = float(os.environ.get("DRIFT_THRESHOLD", "0.05"))
COSMOS_URL = os.environ.get("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.environ.get("COSMOS_KEY", "")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")


@dataclass
class DriftReport:
    evaluated_at: str
    window_days: int
    incident_count: int
    correct_diagnoses: int
    f1_score: float
    baseline_f1: float
    drift_detected: bool
    drift_magnitude: float
    recommendation: str
    sample_failures: list[dict]


def _compute_f1(tp: int, fp: int, fn: int) -> float:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _load_recent_incidents(days: int = 7) -> list[dict]:
    """Load incidents from Cosmos DB for the evaluation window."""
    if not COSMOS_URL:
        logger.warning("Cosmos not configured — loading golden test set from disk")
        golden_path = Path("monitoring/evaluation/golden_test_set.jsonl")
        if golden_path.exists():
            with open(golden_path) as f:
                return [json.loads(line) for line in f if line.strip()]
        return []

    from azure.cosmos import CosmosClient
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY)
    db = client.get_database_client(os.environ.get("COSMOS_DB", "kinetic-core"))
    container = db.get_container_client("incidents")
    query = "SELECT * FROM c WHERE c.started_at >= @cutoff AND c.outcome != 'NO_FAULT'"
    params = [{"name": "@cutoff", "value": cutoff}]
    return list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))


def evaluate_incidents(incidents: list[dict]) -> DriftReport:
    if not incidents:
        return DriftReport(
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            window_days=7,
            incident_count=0,
            correct_diagnoses=0,
            f1_score=0.0,
            baseline_f1=BASELINE_F1,
            drift_detected=False,
            drift_magnitude=0.0,
            recommendation="No incidents in evaluation window",
            sample_failures=[],
        )

    tp = fp = fn = 0
    failures = []

    for incident in incidents:
        diagnostic = incident.get("stages", {}).get("diagnostic", {})
        ai_fault_code = diagnostic.get("fault_code")
        confirmed_fault = incident.get("confirmed_fault_code")

        if not confirmed_fault:
            continue

        if ai_fault_code == confirmed_fault:
            tp += 1
        elif ai_fault_code and ai_fault_code != confirmed_fault:
            fp += 1
            failures.append({
                "incident_id": incident.get("incident_id"),
                "ai_predicted": ai_fault_code,
                "confirmed": confirmed_fault,
                "confidence": diagnostic.get("confidence", 0.0),
            })
        else:
            fn += 1
            failures.append({
                "incident_id": incident.get("incident_id"),
                "ai_predicted": None,
                "confirmed": confirmed_fault,
                "note": "AI did not flag — missed detection",
            })

    f1 = _compute_f1(tp, fp, fn)
    drift_magnitude = BASELINE_F1 - f1
    drift_detected = drift_magnitude > DRIFT_THRESHOLD

    recommendation = "No action required — model performance within acceptable range."
    if drift_detected:
        recommendation = (
            f"DRIFT DETECTED: F1 dropped {drift_magnitude:.3f} below baseline {BASELINE_F1:.3f}. "
            "Actions: (1) Review failure cases. (2) Check for data distribution shift. "
            "(3) Consider prompt tuning or fine-tuning with recent incidents."
        )

    return DriftReport(
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        window_days=7,
        incident_count=len(incidents),
        correct_diagnoses=tp,
        f1_score=round(f1, 4),
        baseline_f1=BASELINE_F1,
        drift_detected=drift_detected,
        drift_magnitude=round(drift_magnitude, 4),
        recommendation=recommendation,
        sample_failures=failures[:5],
    )


def _send_alert(report: DriftReport) -> None:
    """Send drift alert to Slack webhook."""
    if not SLACK_WEBHOOK:
        logger.warning("No SLACK_WEBHOOK_URL configured — printing alert to stdout")
        print(f"DRIFT ALERT: F1={report.f1_score:.3f}, baseline={report.baseline_f1:.3f}, delta={report.drift_magnitude:.3f}")
        return

    import urllib.request
    payload = json.dumps({
        "text": (
            f":rotating_light: *Kinetic-Core Drift Alert*\n"
            f"F1 Score: `{report.f1_score:.3f}` (baseline: `{report.baseline_f1:.3f}`)\n"
            f"Drop: `{report.drift_magnitude:.3f}` over `{report.incident_count}` incidents\n"
            f"Recommendation: {report.recommendation}"
        )
    }).encode()
    req = urllib.request.Request(SLACK_WEBHOOK, data=payload, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


def run_evaluation(window_days: int = 7) -> DriftReport:
    logger.info(f"Loading incidents for last {window_days} days")
    incidents = _load_recent_incidents(window_days)
    logger.info(f"Loaded {len(incidents)} incidents")

    report = evaluate_incidents(incidents)
    logger.info(f"Evaluation complete: F1={report.f1_score:.4f}, drift={report.drift_detected}")

    report_path = Path(f"monitoring/drift/reports/drift_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report.__dict__, f, indent=2)
    logger.info(f"Report saved → {report_path}")

    if report.drift_detected:
        logger.warning(f"DRIFT DETECTED: {report.recommendation}")
        _send_alert(report)

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluate", action="store_true", default=True)
    parser.add_argument("--window-days", type=int, default=7)
    args = parser.parse_args()
    report = run_evaluation(args.window_days)
    print(json.dumps(report.__dict__, indent=2))
