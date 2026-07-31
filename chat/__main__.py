"""CLI for the Faveod chat agent.

Examples:
  python -m chat "Combien de partenaires qualifiés avons-nous ?"
  python -m chat --interactive
"""

from __future__ import annotations

import argparse
import logging
import sys

from chat.assistant import ChatAssistant


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="faveod-assist", description="Faveod chat agent (Task 6.2)")
    parser.add_argument("prompt", nargs="?", default=None, help="single question to answer")
    parser.add_argument("-i", "--interactive", action="store_true", help="interactive chat loop")
    parser.add_argument("--verbose", action="store_true", help="show tool call logs")
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s", stream=sys.stderr)

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - some consoles do not support reconfigure
            pass

    assistant = ChatAssistant()
    print("Faveod Assist - tapez votre question (Ctrl+C pour quitter).")

    def ask(prompt: str) -> None:
        print("\nVous :", prompt)
        print("Faveod Assist :")
        print(assistant.answer(prompt))

    if args.interactive or args.prompt is None:
        if args.prompt:
            ask(args.prompt)
        while True:
            try:
                line = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAu revoir.")
                return 0
            if not line:
                continue
            ask(line)
        return 0

    ask(args.prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
