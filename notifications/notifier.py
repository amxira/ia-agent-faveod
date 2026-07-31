"""Notification engine (Task 5.1).

Reads the agents' latest outputs, detects NEW high-value tenders (>= threshold)
and high-priority leads (deduplicated via a state file), and dispatches them to
the configured channels: console (always), Slack webhook, Teams webhook and/or
SMTP email. Failures in a channel never crash the check.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any

from notifications import config

log = logging.getLogger(__name__)

STATE_FILE = os.path.join(config.STATE_DIR, "notified.json")


# ---------------------------------------------------------------- loading ---
def _read_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001 - bad JSON must never crash the checker
        log.warning("cannot read %s: %s", path, exc)
        return {}


def _output_file(name: str) -> str:
    return os.path.join(config.OUTPUT_DIR, name)


def load_tenders() -> list[dict]:
    payload = _read_json(_output_file("latest.json"))
    return list(payload.get("reports") or [])


def load_leads() -> list[dict]:
    payload = _read_json(_output_file("priority_leads.json"))
    return list(payload.get("priority_leads") or payload.get("leads") or [])


# ------------------------------------------------------------- detection ---
def _load_state() -> dict[str, list]:
    state = _read_json(STATE_FILE)
    return {"tenders": list(state.get("tenders") or []), "leads": list(state.get("leads") or [])}


def _save_state(state: dict[str, list]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def detect_new_alerts(
    tenders: list[dict] | None = None,
    leads: list[dict] | None = None,
    threshold: float | None = None,
) -> dict:
    """Return {'alerts': [...], 'state': updated}. Marks new items as notified."""
    threshold = threshold if threshold is not None else config.TENDER_ALERT_THRESHOLD
    tenders = tenders if tenders is not None else load_tenders()
    leads = leads if leads is not None else load_leads()

    state = _load_state()
    already = set(state["tenders"])
    alerts = []
    for report in tenders:
        tid = str(report.get("tender_id") or "")
        if tid in already:
            continue
        score = float(report.get("fit_score") or 0.0)
        if score >= threshold:
            alerts.append({"kind": "tender", "id": tid, "score": score, "data": report})
            state["tenders"].append(tid)
        else:
            state["tenders"].append(tid)  # seen; never alert later on the same run

    lead_already = set(state["leads"])
    if config.NOTIFY_ON_LEADS:
        for lead in leads:
            lid = str(lead.get("lead_id") or "")
            if lid in lead_already:
                continue
            if str(lead.get("priority") or "").upper() == config.LEAD_PRIORITY_FILTER.upper():
                alerts.append({"kind": "lead", "id": lid, "score": float(lead.get("lead_score") or 0.0), "data": lead})
            lead_already.add(lid)
        state["leads"] = sorted(lead_already)

    _save_state(state)
    return {"alerts": alerts, "state": state}


# ------------------------------------------------------------- formatting ---
def format_alert(alert: dict) -> str:
    data = alert["data"]
    if alert["kind"] == "tender":
        return (
            f"🚨 HIGH-VALUE TENDER {alert['score']:.0f}% - {data.get('title', '')}\n"
            f"    {data.get('tender_id', '')} | {data.get('country', '')} | deadline: {data.get('deadline') or 'n/a'}\n"
            f"    {data.get('url', '')}"
        )
    return (
        f"⭐ HIGH-PRIORITY LEAD {alert['score']:.0f}% - {data.get('person_name', '')}\n"
        f"    {data.get('job_title', '')} @ {data.get('company', '')} | {data.get('country', '')}\n"
        f"    Event: {data.get('event_name', '')} | {data.get('event_url', '')}"
    )


def build_summary_text(alerts: list[dict]) -> str:
    if not alerts:
        return "Faveod check: no new alerts."
    lines = [f"Faveod intelligence - {len(alerts)} new alert(s):"]
    for alert in alerts:
        lines.append("")
        lines.append(format_alert(alert))
    return "\n".join(lines)


# -------------------------------------------------------------- dispatch ---
def dispatch(text: str, dry_run: bool = False) -> dict[str, bool]:
    results = {"console": True, "slack": False, "teams": False, "email": False}

    print(text)
    if dry_run or not text.strip():
        return results

    if config.SLACK_WEBHOOK:
        results["slack"] = _post_webhook(config.SLACK_WEBHOOK, {"text": text})
    if config.TEAMS_WEBHOOK:
        results["teams"] = _post_webhook(config.TEAMS_WEBHOOK, {"text": text})
    if config.SMTP_HOST and config.SMTP_TO:
        results["email"] = _send_email(text)
    return results


def _post_webhook(url: str, payload: dict) -> bool:
    import requests  # noqa: PLC0415 - heavy import only when a webhook is configured

    try:
        resp = requests.post(url, json=payload, timeout=15)
        ok = resp.status_code in (200, 201, 202)
        if not ok:
            log.warning("webhook %s returned HTTP %s", url, resp.status_code)
        return ok
    except Exception as exc:  # noqa: BLE001 - channel failures must not crash the check
        log.warning("webhook dispatch failed: %s", exc)
        return False


def _send_email(body: str) -> bool:
    try:
        msg = EmailMessage()
        msg["Subject"] = f"Faveod intelligence alerts ({len(body.splitlines())} lines)"
        msg["From"] = config.SMTP_FROM
        msg["To"] = config.SMTP_TO
        msg.set_content(body)
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as server:
            server.ehlo()
            if config.SMTP_USER:
                server.starttls()
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("email dispatch failed: %s", exc)
        return False


def check(
    threshold: float | None = None,
    dry_run: bool = False,
    reset: bool = False,
) -> dict[str, Any]:
    if reset and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        log.info("notification state reset")
    result = detect_new_alerts(threshold=threshold)
    text = build_summary_text(result["alerts"])
    channels = dispatch(text, dry_run=dry_run)
    return {"alerts": result["alerts"], "channels": channels, "text": text}
