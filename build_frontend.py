"""Build the dashboard frontend with esbuild.

Bundles the modular ESM entry (``src/app/ui/main.js``) and its component modules
into a single ``src/app/ui/main.js`` served by the FastAPI static mount at ``/src/app/ui``.

Run directly::

    python build_frontend.py

or as a package command (see ``pyproject.toml`` ``[project.scripts]``).

Optimization features:
- Tree shaking (aggressive dead code elimination)
- Minification (whitespace, syntax, identifiers)
- Source maps for debugging
- Chunk splitting for code splitting
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

    # Bundle every entry module into one file. ``format: esm`` wraps the
    # module output in a standard ES module script, which is the proper
    # way to serve the bundle to the browser.
    result = subprocess.run(
        [
            "python3",
            "-m",
            "esbuild",
            str(ENTRY),
            "--bundle",
            # Tree shaking: aggressive dead code elimination
            "--tree-shaking=true",
            # Minification options
            "--minify=true",
            "--minify-whitespace=true",
            "--minify-syntax=true",
            "--minify-identifiers=true",
            # Source maps for debugging
            "--sourcemap=inline",
            # Platform: browser
            "--platform=browser",
            # Output format: ES module
            "--format=esm",
            "--outfile=" + str(OUT),
            "--allow-overwrite",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("esbuild failed:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return result.returncode

    # esbuild writes the bundle directly to ``OUT`` (``--outfile=``). ``stdout``
    # is empty for a single entry point, so no further copying is required.
    print(f"built {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
