"""Tests that runner.py correctly builds Judge objects from JudgeConfig.

These are synchronous tests that wrap the async benchmark in :func:`anyio.run`,
matching the project's existing anyio usage (no pytest-asyncio dependency).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import anyio


class FakeEngine:
    """A stand-in engine: builds from config, async close(), no network I/O.

    Instances record themselves in ``FakeEngine.instances`` so the test can count
    how many engines were constructed after the ``patch()`` block exits. (A
    ``patch()`` handle can't be a trackable MagicMock here: Python 3.11 raises
    ``TypeError: Can't pass kwargs to a mock we aren't creating`` when ``new=``
    (the ``FakeEngine`` class) is set, and the handle has no ``call_count``.)

    Each constructed instance has an AsyncMock ``close()`` so the runner's
    ``await engine.close()`` in its ``finally`` block works without a network.
    """

    instances = []

    def __init__(self, config):
        self.config = config
        self.close = AsyncMock()
        FakeEngine.instances.append(self)
        self.close = AsyncMock()

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
    assert judge_call.kwargs["name"] == "judge"
    assert judge_arg is not None
    assert judge_arg.config.base_url == "http://judge:11434"


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

    FakeEngine.instances = []

    with patch("local_llm_benchmark.runner.OpenAICompatEngine", FakeEngine), \
         patch("local_llm_benchmark.benchmarks.speed.benchmark_speed", new=AsyncMock(return_value=[_make_row()])), \
         patch("local_llm_benchmark.runner.evaluate_quality", new=AsyncMock(return_value=MagicMock())):
        anyio.run(run_benchmark, config)

    # Two engines opened (one judge + one model).
    assert len(FakeEngine.instances) == 2
    # Each opened engine must have had its async close() awaited.
    for instance in FakeEngine.instances:
        assert instance.close.await_count == 1


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
    judge_constructions = [c for c in Judge_cls.call_args_list]
    assert len(judge_constructions) == 2
    names = {c.kwargs["name"] for c in judge_constructions}
    assert names == {"judge-a", "judge-b"}
    for c in judge_constructions:
        assert c.kwargs["engine"] is not None
        assert c.kwargs["engine"].config.base_url == "http://" + c.kwargs["name"] + ":11434"
