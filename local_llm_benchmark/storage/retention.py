"""Retention module (ADR-015, ADR-019).

Age-based cleanup of Parquet result files. Disabled by default — callers opt
in by passing a ``retention_days`` value (``None`` keeps every run forever).

Example:
    >>> from local_llm_benchmark.storage import retention
    >>> retention.cleanup(results_dir, retention_days=30)  # delete > 30d old
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from local_llm_benchmark.errors import ConfigurationError


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _delete(path: Path) -> None:
    try:
        path.unlink()
    except OSError as exc:
        raise ConfigurationError(f"failed to remove {path}: {exc}") from exc


def _expired_paths(results_dir: Path, retention_days: Optional[float]) -> List[Path]:
    """Return Parquet paths older than ``retention_days`` days.

    ``retention_days`` of ``None`` returns an empty list (retain all runs).
    """
    if retention_days is None:
        return []
    cutoff = _now() - retention_days
    if not results_dir.exists():
        return []
    return [
        path
        for path in sorted(results_dir.glob("*.parquet"))
        if path.stat().st_size > 0
        and path.stat().st_mtime < cutoff.timestamp()
    ]


def cleanup(results_dir: Path, retention_days: Optional[float] = None) -> List[Path]:
    """Delete runs older than ``retention_days`` days.

    Returns the list of removed paths (empty when nothing was removed).
    """
    expired = _expired_paths(Path(results_dir), retention_days)
    for path in expired:
        _delete(path)
    return expired
