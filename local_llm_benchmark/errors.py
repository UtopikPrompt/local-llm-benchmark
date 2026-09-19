"""Exception types for local-llm-benchmark."""

from __future__ import annotations

import json


class BenchmarkError(Exception):
    """Base class for all benchmark errors."""


class ConfigurationError(BenchmarkError):
    """Raised when the CLI configuration is invalid."""


class EngineError(BenchmarkError):
    """Raised when an engine fails to run or respond."""


class QualityError(BenchmarkError):
    """Raised when a quality metric cannot be computed."""


class StorageError(BenchmarkError):
    """Raised when token/run storage fails."""


class CacheError(BenchmarkError):
    """Raised when the shared cache fails."""


class RetentionError(BenchmarkError):
    """Raised when retention/eviction fails."""


class JsonEncoder(json.JSONEncoder):
    """JSON encoder that handles non-serializable values."""

    def default(self, obj):  # noqa: D401
        if isinstance(obj, set):
            return sorted(obj, key=str)
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        return super().default(obj)
