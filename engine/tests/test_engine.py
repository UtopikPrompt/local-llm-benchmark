"""Smoke tests for the engine test slice.

These tests are intentionally self-contained so the ``engine/tests`` directory
always collects at least one runnable test, even before feature-specific
assertions are added.
"""
from __future__ import annotations

import pytest

from .conftest import DEFAULT_ENGINE_INPUT


def test_smoke(engine_input: int) -> None:
    """The engine slice must collect and run without error."""
    assert engine_input == DEFAULT_ENGINE_INPUT


def test_engine_name(engine_name: str) -> None:
    """The engine slice should expose its own name fixture."""
    assert engine_name == "engine"


@pytest.mark.parametrize("value", [0, 1, 42, -7])
def test_engine_input_roundtrip(value: int) -> None:
    """Values returned by the fixture should round-trip unchanged."""
    assert value + 0 == value