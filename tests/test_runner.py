"""Unit tests for local_llm_benchmark.runner — benchmark orchestration."""

import anyio

import pytest

from local_llm_benchmark.config import BenchmarkConfig, EngineConfig
from local_llm_benchmark.engines.base import Engine
from local_llm_benchmark.runner import _select_tasks, run_benchmark


class StubEngine(Engine):
    """Deterministic stub engine: streams a fixed token, no real network."""

    def __init__(self, answer: str, ttft: float = 0.01, tok_per_s: float = 100.0):
        self.config = EngineConfig(name="stub", base_url="http://stub", model="stub-model")
        self._answer = answer
        self._ttft = ttft
        self._tok_per_s = tok_per_s
        self.closed = False

    def supports_list_models(self):
        return False
    async def chat_completed(self, messages, *, max_tokens=64):
        return self._answer
    def list_models(self, model=None, **kwargs):
        return []

    def chat(self, messages, *, max_tokens=64, stream=False, **kwargs):
        if stream:
            return self._stream()
        return {"id": "stub", "choices": [{"index": 0, "message": {"role": "assistant", "content": self._answer}, "finish_reason": "stop"}]}

    def _stream(self):
        class Stream:
            async def __aiter__(self):
                yield {"token": self._answer}
        return Stream()

    def serve(self, **kwargs):
        pass

    def unload_model(self, **kwargs):
        pass

    async def close(self):
        self.closed = True


def make_config(engines=None, judges=None, tasks=".", task=None, timeout=60.0, max_concurrent=1):
    engines = engines if engines is not None else [EngineConfig("stub", "http://stub", "stub-model")]
    config = BenchmarkConfig(engines=engines, judges=judges, tasks=tasks, task=task, timeout=timeout, max_concurrent=max_concurrent)
    return config


def make_task(prompt="answer 42", expected="42"):
    from local_llm_benchmark.tasks.corpus import Task
    return Task.from_dict(
        {
            "id": "t1",
            "category": "qa",
            "prompt": prompt,
            "expected": expected,
        }
    )


def test_select_tasks_default_corpus():
    config = BenchmarkConfig(engines=[EngineConfig("stub", "http://stub", "m")], tasks=".")
    tasks = _select_tasks(config)
    assert len(tasks) == 8


def test_select_tasks_explicit_dir(tmp_path):
    import json
    (tmp_path / "a.json").write_text('{"id": "a", "category": "qa", "prompt": "a", "expected": "e"}')
    (tmp_path / "b.json").write_text('{"id": "b", "category": "qa", "prompt": "b", "expected": "e2"}')
    config = BenchmarkConfig(engines=[EngineConfig("stub", "http://stub", "m")], tasks=str(tmp_path))
    tasks = _select_tasks(config)
    assert len(tasks) == 2


def test_select_tasks_single_task():
    config = BenchmarkConfig(engines=[EngineConfig("stub", "http://stub", "m")], tasks=".", task="qa-first-iphone-year")
    tasks = _select_tasks(config)
    assert len(tasks) == 1


def test_run_benchmark_returns_rows(tmp_path):
    (tmp_path / "t1.json").write_text('{"id": "t1", "category": "qa", "prompt": "q", "expected": "e"}')
    from local_llm_benchmark.benchmarks import speed

    config = BenchmarkConfig(
        engines=[EngineConfig("stub", "http://stub", "stub-model", timeout=1.0)],
        tasks=str(tmp_path),
        task="t1",
    )

    async def fake_benchmark_speed(engine, task, **kwargs):
        ttft = kwargs.pop("ttft", 0.01)
        return [
            speed.Row(
                engine=engine.config.name,
                model=engine.config.model,
                task_id=task.id,
                category=task.category.value,
                prompt=task.prompt,
                ttft_s=ttft,
                tok_per_s=100.0,
                iters_per_s=100.0,
            )
        ]

    original_benchmark_speed = speed.benchmark_speed
    speed.benchmark_speed = fake_benchmark_speed  # noqa: PLC2901

    try:
        rows = anyio.run(run_benchmark, config)
    finally:
        speed.benchmark_speed = original_benchmark_speed
    assert len(rows) == 1
    assert rows[0].engine == "stub"
    assert rows[0].task_id == "t1"
    assert rows[0].ttft_s == 0.01
    assert rows[0].tok_per_s == 100.0


def test_run_benchmark_no_speed_rows(tmp_path):
    engine = StubEngine(answer="")
    (tmp_path / "t1.json").write_text('{"id": "t1", "category": "qa", "prompt": "q", "expected": "e"}')
    config = BenchmarkConfig(
        engines=[EngineConfig("stub", "http://stub", "stub-model", timeout=1.0)],
        tasks=str(tmp_path),
        task="t1",
    )
    from local_llm_benchmark.benchmarks import speed
    original_benchmark_speed = speed.benchmark_speed

    async def fake_benchmark_speed(engine, task, **kwargs):
        return []

    speed.benchmark_speed = fake_benchmark_speed  # noqa: PLC2901
    try:
        rows = anyio.run(run_benchmark, config)
    finally:
        speed.benchmark_speed = original_benchmark_speed
    assert len(rows) == 1
    assert rows[0].quality_passed is False
    assert "no speed rows" in rows[0].quality_note


def test_run_benchmark_engines_cross_product(tmp_path):
    task = make_task(prompt="q", expected="e")
    (tmp_path / "t1.json").write_text('{"id": "t1", "category": "qa", "prompt": "q", "expected": "e"}')
    config = BenchmarkConfig(
        engines=[
            EngineConfig("stub", "http://stub", "stub-model", timeout=1.0),
        ],
        tasks=str(tmp_path),
        task="t1",
    )
    from local_llm_benchmark.benchmarks import speed
    original_benchmark_speed = speed.benchmark_speed

    async def fake_benchmark_speed(engine, task, **kwargs):
        return [
            speed.Row(
                engine=engine.config.name,
                model=engine.config.model,
                task_id=task.id,
                category=task.category.value,
                prompt=task.prompt,
                ttft_s=0.01,
                tok_per_s=100.0,
                iters_per_s=100.0,
            )
        ]

    speed.benchmark_speed = fake_benchmark_speed  # noqa: PLC2901
    try:
        rows = anyio.run(run_benchmark, config)
    finally:
        speed.benchmark_speed = original_benchmark_speed
    assert len(rows) == 1


def test_parse_args_defaults():
    from local_llm_benchmark.runner import _parse_args
    args = _parse_args([])
    assert args.format == "json"
    assert args.timeout == 60.0
    assert args.max_concurrent == 1
    assert args.trials == 3
    assert args.task_dir == "."


def test_parse_args_base_url():
    from local_llm_benchmark.runner import _parse_args
    args = _parse_args(["--base-url", "http://x", "--model", "m", "--engine", "e"])
    assert args.base_url == "http://x"
    assert args.model == "m"
    assert args.engine == "e"


def test_build_config_requires_config_or_args():
    from local_llm_benchmark.runner import _build_config, _parse_args
    args = _parse_args([])
    with pytest.raises(ValueError):
        _build_config(args)


def test_build_config_with_args():
    from local_llm_benchmark.runner import _build_config, _parse_args
    args = _parse_args(["--base-url", "http://x", "--model", "m", "--engine", "e", "--format", "csv"])
    config = _build_config(args)
    assert len(config.engines) == 1
    assert config.engines[0].name == "e"
    assert config.engines[0].base_url == "http://x"
    assert config.engines[0].model == "m"
    assert config.format == "csv"
    assert config.max_concurrent == 1


def test_build_config_with_judge():
    from local_llm_benchmark.runner import _build_config, _parse_args
    args = _parse_args([
        "--base-url", "http://x", "--model", "m", "--engine", "e",
        "--judge", "judge1", "--judge-url", "http://judge", "--judge-model", "jmodel",
    ])
    config = _build_config(args)
    assert len(config.judges) == 1
    assert config.judges[0].name == "judge1"
    assert config.judges[0].base_url == "http://judge"
    assert config.judges[0].model == "jmodel"


def test_build_config_with_config_file(tmp_path):
    from local_llm_benchmark.runner import _build_config, _parse_args
    import yaml
    config_data = {
        "engines": [{"name": "ollama", "base_url": "http://localhost:11434", "model": "gemma4:e2b"}],
        "tasks": ".",
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_data))
    args = _parse_args(["--config", str(config_path)])
    config = _build_config(args)
    assert len(config.engines) == 1
    assert config.engines[0].name == "ollama"
