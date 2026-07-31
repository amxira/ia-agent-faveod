"""Structured output generation (Task 2.4): JSONL history + latest / high-value dumps."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from tender_hunter import config
from tender_hunter.models import FaveodReport

log = logging.getLogger(__name__)

_HIGH_VALUE_THRESHOLD = 80.0


def _dump(report: FaveodReport) -> dict:
    return report.model_dump(mode="json")


def write_reports(reports: list[FaveodReport]) -> dict:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    jsonl_path = os.path.join(config.OUTPUT_DIR, "reports.jsonl")
    with open(jsonl_path, "a", encoding="utf-8") as fh:
        for report in reports:
            fh.write(json.dumps(_dump(report), ensure_ascii=False) + "\n")

    latest = sorted(reports, key=lambda r: r.fit_score, reverse=True)
    payload = {
        "generated_at": stamp,
        "run_id": stamp,
        "report_count": len(latest),
        "reports": [_dump(r) for r in latest],
    }
    with open(os.path.join(config.OUTPUT_DIR, "latest.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    high_value = [r for r in latest if r.fit_score >= _HIGH_VALUE_THRESHOLD]
    with open(os.path.join(config.OUTPUT_DIR, "high_value.json"), "w", encoding="utf-8") as fh:
        json.dump({"generated_at": stamp, "high_value": [_dump(r) for r in high_value]}, fh, ensure_ascii=False, indent=2)

    log.info("wrote %d report(s) to %s (high-value >= %d%%: %d)", len(latest), jsonl_path, int(_HIGH_VALUE_THRESHOLD), len(high_value))
    return {"written": len(latest), "high_value": len(high_value)}
