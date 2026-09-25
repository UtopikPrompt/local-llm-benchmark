"""Global runtime configuration for local-llm-benchmark.

This module exposes a single :data:`config` object that holds the paths and
flags used across the CLI. It is deliberately stdlib-only so the CLI remains
dependency-light.

See docs/adr/ADR-001-Project-foundation.md.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Absolute path to the package root (directory containing this file).
PACKAGE_DIR = Path(__file__).resolve().parent

# Path to the prompts directory shipped with the package.
PROMPTS_DIR = PACKAGE_DIR / "prompts"

# Cache directory: one shared, gitignored local cache used by both the CLI
# and the Astro UI (ADR-014, ADR-018).
CACHE_DIR = Path(
    os.environ.get("LOCAL_LLM_BENCHMARK_CACHE", str(
        Path.home() / ".cache" / "local-llm-benchmark"))
)

# Benchmark results directory (gitignored, ADR-015).
RESULTS_DIR = Path(
    os.environ.get("LOCAL_LLM_BENCHMARK_RESULTS",
                   str(Path.cwd() / "benchmark-results"))
)

# Default retention age in days. Disabled by default (ADR-015).
DEFAULT_RETENTION_DAYS = None


def cache_dir() -> Path:
    """Return the resolved cache directory, creating it if needed."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def results_dir() -> Path:
    """Return the resolved results directory, creating it if needed."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


def is_windows() -> bool:
    """Whether the current platform is Windows."""
    return sys.platform == "win32"
