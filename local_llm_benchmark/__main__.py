"""The front door of the project.

Running ``python -m local_llm_benchmark`` launches the browser UI, which is the
intended way to start the project. The UI is the *front door*: it mounts the
JSON API (:mod:`local_llm_benchmark.api`) and serves the dashboard, and the API
talks to the core modules.
"""

from __future__ import annotations

import argparse


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the launcher."""
    parser = argparse.ArgumentParser(description="Launch the Local LLM Benchmark dashboard.")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Launch the web dashboard."""
    from local_llm_benchmark.server.api.controller import run_server

    args = _parse_args(argv)
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
