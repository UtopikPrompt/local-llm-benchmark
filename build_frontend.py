"""Build the dashboard frontend with esbuild.

Bundles the modular ESM entry (``web/ui/app.js``) and its component modules
into a single ``web/ui/main.js`` served by the FastAPI static mount at ``/web``.

Run directly::

    python build_frontend.py

or as a package command (see ``pyproject.toml`` ``[project.scripts]``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UI = ROOT / "web" / "ui"
ENTRY = UI / "app.js"
OUT = UI / "main.js"


def main() -> int:
    if not ENTRY.exists():
        print(f"error: entry not found: {ENTRY}", file=sys.stderr)
        return 1

    # Bundle every entry module into one file. ``format: iife`` wraps the
    # module output in a classic script (not a `<script type="module">`), which
    # keeps the DOMContentLoaded bootstrap working exactly as before.
    result = subprocess.run(
        [
            "python3",
            "-m",
            "esbuild",
            str(ENTRY),
            "--bundle",
            "--format=iife",
            "--outfile=str:" + str(OUT),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("esbuild failed:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return result.returncode

    print(f"built {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
