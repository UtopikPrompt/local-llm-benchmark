"""Tests for :mod:`engine.core`."""

import pytest

from engine.core import Engine, EngineConfig, StepResult


def test_config_rejects_non_positive_iterations() -> None:
    with pytest.raises(ValueError, match="max_iterations"):
        EngineConfig(max_iterations=0)


def test_config_rejects_negative_iterations() -> None:
    with pytest.raises(ValueError, match="max_iterations"):
        EngineConfig(max_iterations=-1)


def test_empty_engine_fold_returns_seed() -> None:
    engine = Engine()
    assert engine.fold(seed=7) == 7


def test_run_runs_steps_in_order() -> None:
    engine = Engine().add_step("double", lambda v: v * 2).add_step(
        "plus_one", lambda v: v + 1
    )
    results = engine.run(seed=3)

    assert results == [
        StepResult(name="double", value=6, ok=True),
        StepResult(name="plus_one", value=7, ok=True),
    ]


def test_fold_applies_pipeline() -> None:
    engine = Engine().add_step("double", lambda v: v * 2)
    assert engine.fold(seed=5) == 10


def test_run_rejects_negative_seed() -> None:
    with pytest.raises(ValueError, match="seed"):
        Engine().add_step("noop", lambda v: v).run(seed=-1)


def test_run_rejects_too_many_steps() -> None:
    engine = Engine(EngineConfig(max_iterations=2))
    for i in range(3):
        engine.add_step(f"step_{i}", lambda v: v)
    with pytest.raises(ValueError, match="max_iterations"):
        engine.run()


def test_process_maps_over_items() -> None:
    engine = Engine().add_step("double", lambda v: v * 2)
    assert engine.process([1, 2, 3]) == [2, 4, 6]


def test_add_step_returns_engine_for_fluent_api() -> None:
    engine = Engine()
    assert engine.add_step("noop", lambda v: v) is engine