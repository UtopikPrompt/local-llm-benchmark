"""Tests that runner.py correctly builds Judge objects from JudgeConfig.

These are synchronous tests that wrap the async benchmark in :func:`anyio.run`,
matching the project's existing anyio usage (no pytest-asyncio dependency).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import anyio


class FakeEngine:
    """A stand-in engine: builds from config, async close(), no network I/O."""

    def __init__(self, config):
        self.config = config

    async def close(self):
        pass


from local_llm_benchmark.config import BenchmarkConfig, EngineConfig, JudgeConfig
from local_llm_benchmark.results import Row
from local_llm_benchmark.runner import run_benchmark


def _make_row():
    return Row(engine="engine", model="model", task_id="qa-first-iphone-year", category="qa", prompt="p", expected="2007", quality_passed=False, quality_note="")


def _make_config(judges):
    return BenchmarkConfig(
        engines=[
            EngineConfig("engine", "http://engine:11434", "model", timeout=30.0, max_concurrent=1)
        ],
        judges=list(judges),
        tasks=".",
    )


def test_run_benchmark_with_judge_builds_real_judge():
    """run_benchmark must convert each JudgeConfig into a real Judge object
    (wrapping an OpenAICompatEngine) and pass it to the quality scorer."""
    config = _make_config([JudgeConfig("judge", "http://judge:11434", "judge_model", timeout=30.0)])

    # FakeEngine is a real engine class (async close), so no await error.
    with patch("local_llm_benchmark.runner.OpenAICompatEngine", FakeEngine), \
         patch("local_llm_benchmark.runner.Judge") as Judge_cls, \
         patch("local_llm_benchmark.benchmarks.speed.benchmark_speed", new=AsyncMock(return_value=[_make_row()])), \
         patch("local_llm_benchmark.runner.evaluate_quality", new=AsyncMock(return_value=MagicMock())) as q:

        anyio.run(run_benchmark, config)

    # One Judge per judge configuration, constructed with the right engine + name.
    judge_calls = [c for c in Judge_cls.call_args_list if c.kwargs.get("name") == "judge"]
    assert len(judge_calls) == 1
    judge_call = judge_calls[0]
    judge_arg = judge_call.kwargs["engine"]  # the constructed Judge
    assert judge_arg is not None
    assert judge_arg.name == "judge"
    assert judge_arg.engine.config.base_url == "http://judge:11434"


def test_run_benchmark_without_judge_passes_none():
    """Without judges, no Judge is constructed and `judge` is None."""
    config = _make_config([])
    with patch("local_llm_benchmark.runner.OpenAICompatEngine", FakeEngine), \
         patch("local_llm_benchmark.runner.Judge") as Judge_cls, \
         patch("local_llm_benchmark.benchmarks.speed.benchmark_speed", new=AsyncMock(return_value=[_make_row()])), \
         patch("local_llm_benchmark.runner.evaluate_quality", new=AsyncMock(return_value=MagicMock())) as q:

        anyio.run(run_benchmark, config)

    Judge_cls.assert_not_called()
    judge_arg = q.call_args.kwargs["judge"]
    assert judge_arg is None


def test_run_benchmark_closes_judge_engine():
    """Judges engines are opened and closed within the run."""
    config = _make_config([JudgeConfig("judge", "http://judge:11434", "judge_model", timeout=30.0)])

    with patch("local_llm_benchmark.runner.OpenAICompatEngine") as eng_cls, \
         patch("local_llm_benchmark.benchmarks.speed.benchmark_speed", new=AsyncMock(return_value=[_make_row()])), \
         patch("local_llm_benchmark.runner.evaluate_quality", new=AsyncMock(return_value=MagicMock())):

        anyio.run(run_benchmark, config)

    # Two engines opened (one judge + one model).
    assert eng_cls.call_count == 2
    # Each opened engine must have had its async close() awaited.
    for call in eng_cls.call_args_list:
        assert call.return_value.close.await_count == 1


def test_run_benchmark_multiple_judges():
    """Each judge configuration yields a distinct Judge with its own engine."""
    config = _make_config([
        JudgeConfig("judge-a", "http://judge-a:11434", "judge_model_a", timeout=30.0),
        JudgeConfig("judge-b", "http://judge-b:11434", "judge_model_b", timeout=30.0),
    ])

    with patch("local_llm_benchmark.runner.OpenAICompatEngine", FakeEngine), \
         patch("local_llm_benchmark.runner.Judge") as Judge_cls, \
         patch("local_llm_benchmark.benchmarks.speed.benchmark_speed", new=AsyncMock(return_value=[_make_row()])), \
         patch("local_llm_benchmark.runner.evaluate_quality") as q:

        rows = anyio.run(run_benchmark, config)

    assert len(rows) == 8  # one engine x eight tasks
    # Each judge configuration must be constructed into a distinct Judge with its own engine.
    judge_constructions = [c.kwargs["judge"] for c in Judge_cls.call_args_list]
    assert len(judge_constructions) == 2
    names = {judge.name for judge in judge_constructions}
    assert names == {"judge-a", "judge-b"}
    for judge in judge_constructions:
        assert judge is not None
        assert judge.engine.config.base_url == judge.name + ":11434"
