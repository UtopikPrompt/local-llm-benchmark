"""Tests for :class:`engine.core.EngineConfig`."""

from engine.core import EngineConfig


def test_config_defaults() -> None:
    config = EngineConfig()
    assert config.max_iterations == 100
    assert config.parallel is False