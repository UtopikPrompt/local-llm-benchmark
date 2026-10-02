"""Shared pytest fixtures for the engine test slice.

Keeping fixtures local to this slice means tests never reach outside the
``engine`` feature, preserving the isolation that vertical-slice architecture
relies on.
"""
from __future__ import annotations

from typing import Final

import pytest

DEFAULT_ENGINE_INPUT: Final[int] = 42


@pytest.fixture
def engine_input() -> int:
    """Provide a deterministic input value for engine tests."""
    return DEFAULT_ENGINE_INPUT


@pytest.fixture
def engine_name() -> str:
    """Provide the human-readable name of the engine under test."""
    return "engine"