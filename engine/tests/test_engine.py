"""Tests for the core engine evaluation logic."""

from __future__ import annotations

import pytest

from .conftest import DEFAULT_ENGINE_INPUT

# Localized imports so the test module imports cleanly even if a
# dependency (e.g. llama_cpp) is not installed.
pytest.importorskip("llama_cpp")


def test_default_engine_input_has_required_keys() -> None:
    """The shared default input must contain all required fields."""
    for key in ("query", "model", "temperature", "max_tokens"):
        assert key in DEFAULT_ENGINE_INPUT


@pytest.mark.parametrize("input_override", [
    {"query": "hello"},
    {"model": "llama3.1:8b"},
])
def test_engine_runs(input_override: dict) -> None:
    """Smoke-test that the engine can be invoked with a default input."""
    from engine.core.engine import run_query

    merged = {**DEFAULT_ENGINE_INPUT, **input_override}
    result = run_query(**merged)
    assert result is not None
    assert isinstance(result, str)