"""Structured output generation (Task 3.3): JSONL history + latest + qualified dump."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from partner_scout import config
from partner_scout.models import QualifiedPartner

log = logging.getLogger(__name__)


def _dump(partner: QualifiedPartner) -> dict:
    return partner.model_dump(mode="json")


def write_partners(partners: list[QualifiedPartner]) -> dict:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    jsonl_path = os.path.join(config.OUTPUT_DIR, "partners.jsonl")
    with open(jsonl_path, "a", encoding="utf-8") as fh:
        for partner in partners:
            fh.write(json.dumps(_dump(partner), ensure_ascii=False) + "\n")

    latest = sorted(partners, key=lambda p: p.affinity_score, reverse=True)
    payload = {
        "generated_at": stamp,
        "run_id": stamp,
        "company_count": len(latest),
        "qualified_count": sum(1 for p in latest if p.qualified),
        "partners": [_dump(p) for p in latest],
    }
    with open(os.path.join(config.OUTPUT_DIR, "partners_latest.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    qualified = [p for p in latest if p.qualified]
    with open(os.path.join(config.OUTPUT_DIR, "qualified_partners.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {"generated_at": stamp, "qualified_count": len(qualified), "qualified": [_dump(p) for p in qualified]},
            fh,
            ensure_ascii=False,
            indent=2,
        )

    log.info("wrote %d partner(s) to %s (qualified >= %d%%: %d)", len(latest), jsonl_path, int(config.AFFINITY_THRESHOLD), len(qualified))
    return {"written": len(latest), "qualified": len(qualified)}
