"""Structured output generation (Task 4.3): event feed + prospect cards."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from event_mapper import config
from event_mapper.models import ITEvent, ProspectCard

log = logging.getLogger(__name__)


def _dump(obj) -> dict:
    return obj.model_dump(mode="json")


def write_outputs(events: list[ITEvent], leads: list[ProspectCard]) -> dict:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    events_path = os.path.join(config.OUTPUT_DIR, "events.jsonl")
    with open(events_path, "a", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(_dump(event), ensure_ascii=False) + "\n")
    with open(os.path.join(config.OUTPUT_DIR, "events_latest.json"), "w", encoding="utf-8") as fh:
        json.dump({"generated_at": stamp, "event_count": len(events), "events": [_dump(e) for e in events]}, fh, ensure_ascii=False, indent=2)

    leads_path = os.path.join(config.OUTPUT_DIR, "leads.jsonl")
    with open(leads_path, "a", encoding="utf-8") as fh:
        for lead in leads:
            fh.write(json.dumps(_dump(lead), ensure_ascii=False) + "\n")

    latest = sorted(leads, key=lambda l: l.lead_score, reverse=True)
    with open(os.path.join(config.OUTPUT_DIR, "leads_latest.json"), "w", encoding="utf-8") as fh:
        json.dump({"generated_at": stamp, "lead_count": len(latest), "leads": [_dump(l) for l in latest]}, fh, ensure_ascii=False, indent=2)

    high = [l for l in latest if l.lead_score >= config.PRIORITY_THRESHOLD]
    with open(os.path.join(config.OUTPUT_DIR, "priority_leads.json"), "w", encoding="utf-8") as fh:
        json.dump({"generated_at": stamp, "priority_count": len(high), "priority_leads": [_dump(l) for l in high]}, fh, ensure_ascii=False, indent=2)

    log.info("wrote %d event(s) to %s and %d lead(s) to %s (high-priority >= %d%%: %d)",
             len(events), events_path, len(latest), leads_path, int(config.PRIORITY_THRESHOLD), len(high))
    return {"events": len(events), "leads": len(latest), "priority": len(high)}
