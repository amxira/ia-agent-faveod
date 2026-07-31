"""CLI for Event Mapper & Lead Profiler (Agent 3).

Examples:
  python -m event_mapper run                            # offline demo (sample events)
  python -m event_mapper run --source ten_times         # live via TenTimes
  python -m event_mapper run --source searxng           # live via SearXNG news
  python -m event_mapper run --countries Morocco Senegal --limit 10
  python -m event_mapper run --interval 60              # rescan hourly
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from event_mapper import config
from event_mapper.graph import build_components, run_once
from event_mapper.output.writer import write_outputs


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        fh = logging.FileHandler(f"{config.LOG_DIR}/event_mapper.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        logging.getLogger().addHandler(fh)
    except Exception:  # noqa: BLE001 - logging must never crash the CLI
        pass


def _run(args: argparse.Namespace) -> int:
    if args.source:
        config.EVENT_SOURCE = args.source
    if args.countries:
        config.EVENT_COUNTRIES = args.countries
    if args.days and args.days > 0:
        config.UPCOMING_DAYS = args.days

    if args.interval and args.interval > 0:
        while True:
            _run_once(args.limit, args.source)
            print(f"\n[schedule] sleeping {args.interval} min ... (Ctrl+C to stop)")
            try:
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                print("\n[schedule] stopped")
                return 0
    _run_once(args.limit, args.source)
    return 0


def _run_once(limit: int, source: str | None) -> None:
    print(f"[event-mapper] source={config.EVENT_SOURCE} countries={config.EVENT_COUNTRIES} model={config.LLM_MODEL}")
    state = run_once(build_components(source=source))
    leads = state.get("leads", [])

    if limit and limit > 0:
        leads = leads[:limit]

    counts = write_outputs(state.get("events", []), leads)

    print(f"\n=== Agent 3 - Event Mapper & Lead Profiler: {counts['leads']} lead(s) ===")
    for card in sorted(leads, key=lambda l: l.lead_score, reverse=True):
        flag = " [MANUAL REVIEW]" if card.requires_manual_review else ""
        dm = " [DECISION-MAKER]" if card.decision_maker else ""
        print(f"  {card.lead_score:5.1f}%  {card.priority:<16} {card.lead_id:<14} {card.person_name[:28]:<28} {card.job_title[:32]:<32} {card.company[:28]:<28} {card.country:<18}{dm}{flag}")
    print(f"  -> JSONL: {config.OUTPUT_DIR}/leads.jsonl | latest: {config.OUTPUT_DIR}/leads_latest.json | priority: {config.OUTPUT_DIR}/priority_leads.json")


def _list_sources() -> int:
    from event_mapper.ingest.registry import AVAILABLE_SOURCES

    for s in ["sample"] + sorted(AVAILABLE_SOURCES):
        print(s)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="event-mapper", description="Agent 3 - Event Mapper & Lead Profiler (Faveod)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="discover IT events, extract speakers, score leads")
    run_p.add_argument("--source", default=None, help="event backend (sample, ten_times, eventbrite, luma, news)")
    run_p.add_argument("--countries", nargs="+", default=None, help="target countries")
    run_p.add_argument("--days", type=int, default=0, help="keep only events starting within the next N days (0 = all)")
    run_p.add_argument("--limit", type=int, default=0, help="max leads to emit (0 = all)")
    run_p.add_argument("--interval", type=float, default=0, help="rescan every N minutes (0 = once)")
    run_p.set_defaults(func=_run)

    src_p = sub.add_parser("sources", help="list available event backends")
    src_p.set_defaults(func=lambda a: _list_sources())

    args = parser.parse_args(argv)
    _setup_logging()
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - some consoles do not support reconfigure
            pass
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
