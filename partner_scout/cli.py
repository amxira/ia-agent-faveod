"""CLI for Partner Scout (Agent 2).

Examples:
  python -m partner_scout run                       # offline demo (sample corpus)
  python -m partner_scout run --source searxng      # live search via self-hosted SearXNG
  python -m partner_scout run --countries Morocco Senegal --limit 12
  python -m partner_scout run --interval 60         # rescan hourly
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from partner_scout import config
from partner_scout.graph import build_components, run_once
from partner_scout.output.writer import write_partners


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        fh = logging.FileHandler(f"{config.LOG_DIR}/partner_scout.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        logging.getLogger().addHandler(fh)
    except Exception:  # noqa: BLE001 - logging must never crash the CLI
        pass


def _run(args: argparse.Namespace) -> int:
    if args.source:
        config.SEARCH_SOURCE = args.source
    if args.countries:
        config.TARGET_COUNTRIES = args.countries

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
    print(f"[partner-scout] source={config.SEARCH_SOURCE} countries={config.TARGET_COUNTRIES} model={config.LLM_MODEL}")
    state = run_once(build_components())
    partners = state.get("partners", [])

    if limit and limit > 0:
        partners = partners[:limit]

    write_partners(partners)

    print(f"\n=== Agent 2 - Partner Scout: {len(partners)} company(ies) ===")
    for p in sorted(partners, key=lambda p: p.affinity_score, reverse=True):
        flag = " [MANUAL REVIEW]" if p.requires_manual_review else ""
        tag = " [QUALIFIED]" if p.qualified else (" [DISQUALIFIED]" if p.disqualification_reason else "")
        print(f"  {p.affinity_score:5.1f}%  {p.affinity_grade:<24} {p.partner_id:<12} {p.company_name[:42]:<42} {p.country:<20}{tag}{flag}")
    print(f"  -> JSONL: {config.OUTPUT_DIR}/partners.jsonl | latest: {config.OUTPUT_DIR}/partners_latest.json | qualified: {config.OUTPUT_DIR}/qualified_partners.json")


def _list_sources() -> int:
    from partner_scout.search.registry import AVAILABLE_ENGINES

    for s in ["sample"] + sorted(AVAILABLE_ENGINES):
        print(s)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="partner-scout", description="Agent 2 - Partner Scout (Faveod)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="search, analyze and qualify local IT companies")
    run_p.add_argument("--source", default=None, help="search backend (sample, searxng)")
    run_p.add_argument("--countries", nargs="+", default=None, help="target countries")
    run_p.add_argument("--limit", type=int, default=0, help="max partners to emit (0 = all)")
    run_p.add_argument("--interval", type=float, default=0, help="rescan every N minutes (0 = once)")
    run_p.set_defaults(func=_run)

    src_p = sub.add_parser("sources", help="list available search backends")
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
