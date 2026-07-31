"""CLI for Agent 5 - Notifications.

Examples:
  python -m notifications check                 # detect & dispatch new alerts
  python -m notifications check --threshold 85  # raise the tender alert bar
  python -m notifications check --dry-run       # print only, no channels
  python -m notifications check --reset         # forget already-notified items
  python -m notifications check --interval 60   # re-check every 60 minutes
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from notifications import config
from notifications.notifier import check


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        fh = logging.FileHandler(f"{config.DATA_DIR}/logs/notifications.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        logging.getLogger().addHandler(fh)
    except Exception:  # noqa: BLE001 - logging must never crash the CLI
        pass


def _run(args: argparse.Namespace) -> int:
    if args.interval and args.interval > 0:
        while True:
            _check_once(args)
            print(f"\n[schedule] sleeping {args.interval} min ... (Ctrl+C to stop)")
            try:
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                print("\n[schedule] stopped")
                return 0
    _check_once(args)
    return 0


def _check_once(args: argparse.Namespace) -> None:
    result = check(threshold=args.threshold, dry_run=args.dry_run, reset=args.reset)
    channels = ", ".join(c for c, ok in result["channels"].items() if ok) or "none"
    print(f"[notifications] {len(result['alerts'])} new alert(s) | channels: {channels}")
    if args.reset:
        args.reset = False  # only the first scheduled run resets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notifications", description="Agent 5 - Notifications (Faveod)")
    parser.add_argument("cmd", nargs="?", default="check", choices=["check"], help="action (default: check)")
    parser.add_argument("--threshold", type=float, default=None, help="tender alert threshold (default env TENDER_ALERT_THRESHOLD)")
    parser.add_argument("--dry-run", action="store_true", help="print only; do not call channels")
    parser.add_argument("--reset", action="store_true", help="forget already-notified items before checking")
    parser.add_argument("--interval", type=float, default=0, help="re-check every N minutes (0 = once)")
    args = parser.parse_args(argv)

    _setup_logging()
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
