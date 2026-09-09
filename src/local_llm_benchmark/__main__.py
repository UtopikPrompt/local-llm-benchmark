"""The front door of the project.

Running ``python -m local_llm_benchmark`` launches the browser UI, which is the
intended way to start the project. The UI is the *front door*: it mounts the
JSON API (:mod:`local_llm_benchmark.api`) and serves the dashboard, and the API
talks to the core modules.
"""

from __future__ import annotations


def main() -> None:
    """Launch the web dashboard."""
    from local_llm_benchmark.web.api.controller import run_server

    run_server(host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
