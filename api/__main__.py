"""Run the Faveod REST API with uvicorn.

Examples:
  python -m api                 # http://localhost:8000, docs at /docs
  python -m api --reload        # dev hot-reload
  python -m api --port 9000
  python -m api --host 0.0.0.0  # expose on the network (Docker)
"""

from __future__ import annotations

import argparse


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="faveod-api", description="Faveod intelligence REST API")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="bind port (default 8000)")
    parser.add_argument("--reload", action="store_true", help="enable dev hot-reload")
    args = parser.parse_args(argv)

    import uvicorn  # noqa: PLC0415 - heavy import only at runtime

    uvicorn.run(
        "api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
