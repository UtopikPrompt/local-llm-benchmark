"""Registry of available engines and the OpenAI-compatible request/response types.

The registry maps engine names to classes so the CLI can look up engines by
name without importing optional plugins directly (ADR-003).
"""

from __future__ import annotations

from typing import Callable, Dict, Type

from local_llm_benchmark.engine.base import Engine, EngineConfig


def register_engine(name: str, engine_cls: Type[Engine]) -> None:
    """Register an engine class under ``name``."""
    ENGINES[name] = engine_cls


def get_engine_class(name: str) -> Type[Engine]:
    """Return the engine class registered under ``name``."""
    try:
        return ENGINES[name]
    except KeyError as exc:
        from local_llm_benchmark.errors import ConfigurationError

        raise ConfigurationError(f"unknown engine: {name!r}") from exc


def available_engines() -> Dict[str, Type[Engine]]:
    """Return the mapping of registered engine name to class."""
    return dict(ENGINES)


def engine_names() -> list[str]:
    """Return the sorted list of registered engine names."""
    return sorted(ENGINES)


# Registry of known engines. Concrete engines register themselves on import.
ENGINES: Dict[str, Type[Engine]] = {}
