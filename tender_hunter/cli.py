"""CLI for Tender Hunter (Agent 1).

Examples:
  python -m tender_hunter run                      # sources from .env, once
  python -m tender_hunter run --sources sample     # offline demo
  python -m tender_hunter run --sources world_bank ebrd --interval 60
  python -m tender_hunter sources                  # list available sources
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from tender_hunter import config
from tender_hunter.graph import build_components, run_once
from tender_hunter.ingest.registry import AVAILABLE_SOURCES
from tender_hunter.output.report import write_reports


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        fh = logging.FileHandler(f"{config.LOG_DIR}/tender_hunter.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        logging.getLogger().addHandler(fh)
    except Exception:  # noqa: BLE001 - logging must never crash the CLI
        pass


def _run(args: argparse.Namespace) -> int:
    if args.sources:
        config.SOURCES = args.sources
    if args.days and args.days > 0:
        config.RECENT_DAYS = args.days

    if args.interval and args.interval > 0:
        while True:
            _run_once(args.limit)
            print(f"\n[schedule] sleeping {args.interval} min ... (Ctrl+C to stop)")
            try:
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                print("\n[schedule] stopped")
                return 0
    _run_once(args.limit)
    return 0


def _run_once(limit: int) -> None:
    print(f"[tender-hunter] sources={config.SOURCES} model={config.LLM_MODEL} embed={config.EMBEDDING_PROVIDER}")
    state = run_once(build_components())
    reports = state.get("reports", [])

    if limit and limit > 0:
        reports = reports[:limit]

    write_reports(reports)

    print(f"\n=== Agent 1 - Tender Hunter: {len(reports)} report(s) ===")
    for report in sorted(reports, key=lambda r: r.fit_score, reverse=True):
        flag = " [MANUAL REVIEW]" if report.requires_manual_review else ""
        print(f"  {report.fit_score:5.1f}%  {report.fit_grade:<22} {report.tender_id:<14} {report.title[:70]}{flag}")
    print(f"  -> JSONL: {config.OUTPUT_DIR}/reports.jsonl | latest: {config.OUTPUT_DIR}/latest.json | high-value: {config.OUTPUT_DIR}/high_value.json")


def _list_sources() -> int:
    for s in ["sample"] + sorted(AVAILABLE_SOURCES):
        print(s)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tender-hunter", description="Agent 1 - Tender Hunter (Faveod)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="scrape, analyze and score tenders")
    run_p.add_argument("--sources", nargs="+", default=None, help="source names (sample, world_bank, ebrd, afdb, imf)")
    run_p.add_argument("--days", type=int, default=0, help="keep only tenders published within the last N days (0 = all)")
    run_p.add_argument("--limit", type=int, default=0, help="max reports to emit (0 = all)")
    run_p.add_argument("--interval", type=float, default=0, help="rescan every N minutes (0 = once)")
    run_p.set_defaults(func=_run)

    src_p = sub.add_parser("sources", help="list available sources")
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
