"""Unit tests for local_llm_benchmark.server.api.services — HTTP-free logic."""

import anyio
import pytest
from pathlib import Path

from local_llm_benchmark.server.api import services


def test_new_engine_from_request():
    engine = services._new_engine_from_request(
        {"base_url": "http://x", "model": "m", "timeout": 10, "max_concurrent": 2},
        services.Defaults(),
    )
    assert engine.name == "ollama"
    assert engine.base_url == "http://x"
    assert engine.model == "m"
    assert engine.timeout == 10
    assert engine.max_concurrent == 2


def test_new_engine_from_request_defaults():
    engine = services._new_engine_from_request(
        {"base_url": "http://x", "model": "m"},
        services.Defaults(),
    )
    assert engine.timeout == services.DEFAULT_TIMEOUT
    assert engine.max_concurrent == services.DEFAULT_MAX_CONCURRENT


def test_new_judge_from_request_none():
    judge = services._new_judge_from_request(
        {"base_url": "http://x", "model": "m"}, services.Defaults()
    )
    assert judge is None


def test_new_judge_from_request_snake_case():
    judge = services._new_judge_from_request(
        {"judge_url": "http://judge", "judge_model": "jmodel"},
        services.Defaults(),
    )
    assert judge.name == "judge"
    assert judge.base_url == "http://judge"
    assert judge.model == "jmodel"


def test_new_judge_from_request_camel_case():
    judge = services._new_judge_from_request(
        {"judgeUrl": "http://judge", "judgeModel": "jmodel"},
        services.Defaults(),
    )
    assert judge is not None
    assert judge.base_url == "http://judge"
    assert judge.model == "jmodel"


def test_new_judge_from_request_fallback_to_default_model():
    judge = services._new_judge_from_request(
        {"judge_url": "http://judge"},
        services.Defaults(),
    )
    assert judge.model == services.DEFAULT_JUDGE_MODEL


async def test_run_with_configured_engine(monkeypatch, tmp_path):
    import yaml
    from local_llm_benchmark.benchmarks import speed

    row = speed.Row(engine="stub", model="m", task_id="t1", tok_per_s=100.0)
    config = {"engine": "stub"}

    cfg_data = {"engines": [{"name": "stub", "base_url": "http://x", "model": "m"}]}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(cfg_data))

    async def fake_run_benchmark(cfg):
        return [row]

    monkeypatch.setattr(services.runner, "run_benchmark", fake_run_benchmark)
    monkeypatch.setattr(services, "write_report", lambda *a, **k: None)

    result = await services.run(config, config_path=str(config_path))
    assert len(result["rows"]) == 1
    assert result["rows"][0]["task_id"] == "t1"
    assert "output" in result


async def test_run_with_fresh_engine(monkeypatch):
    from local_llm_benchmark.results import Row
    from local_llm_benchmark.benchmarks import speed

    row = Row(engine="ollama", model="m", task_id="t1", tok_per_s=100.0)
    config = {"base_url": "http://x", "model": "m"}

    async def fake_run_benchmark(cfg):
        return [row]

    monkeypatch.setattr(services.runner, "run_benchmark", fake_run_benchmark)
    monkeypatch.setattr(services, "write_report", lambda *a, **k: None)

    result = await services.run(config)
    assert len(result["rows"]) == 1
    assert result["rows"][0]["engine"] == "ollama"


async def test_run_unknown_engine(monkeypatch):
    monkeypatch.setattr(services.runner, "run_benchmark", lambda *a, **k: [])
    monkeypatch.setattr(services, "write_report", lambda *a, **k: None)
    with pytest.raises(services.EngineNotFound):
        await services.run({"engine": "nope"})


async def test_run_missing_base_url_and_model(monkeypatch):
    monkeypatch.setattr(services.runner, "run_benchmark", lambda *a, **k: [])
    with pytest.raises(services.BadRequest):
        await services.run({"engine": ""})


async def test_run_with_judge(monkeypatch):
    from local_llm_benchmark.benchmarks import speed

    row = speed.Row(engine="stub", model="m", task_id="t1", tok_per_s=100.0)


async def test_defaults_returns_dict():
    result = await services.defaults()
    assert "max_concurrent" in result
    assert result["max_concurrent"] == services.DEFAULT_MAX_CONCURRENT


async def test_engines_empty_when_no_config(tmp_path):
    path = tmp_path / "does_not_exist.yaml"
    with pytest.raises(services.EngineNotFound):
        await services.engines(str(path))


async def test_engines_returns_list(tmp_path):
    import yaml

    config_data = {"engines": [{"name": "ollama", "base_url": "http://x", "model": "m"}]}
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config_data))
    result = await services.engines(str(path))
    assert len(result) == 1
    assert result[0]["name"] == "ollama"


async def test_tasks_returns_default_corpus():
    result = await services.tasks()
    assert len(result) == 8
    assert result[0]["category"] in ("doc", "code", "qa", "math", "qa_pair", "qa_answer")


async def test_results_round_trip(tmp_path):
    from local_llm_benchmark.benchmarks import speed
    from local_llm_benchmark.results import Row
    from local_llm_benchmark.report import write_report

    rows = [
        Row(engine="stub", model="a", task_id="t1", tok_per_s=100.0),
        Row(engine="stub", model="b", task_id="t1", tok_per_s=200.0),
    ]
    output = tmp_path / "out.json"
    write_report(rows, str(output), fmt="json")

    # ``services.results`` reads from ``DEFAULT_RESULTS_DIR``; point it at the
    # test's temp dir so the round-trip stays isolated from the real results.
    original_results_dir = services.DEFAULT_RESULTS_DIR
    services.DEFAULT_RESULTS_DIR = str(tmp_path)
    try:
        result = await services.results("a,b", "benchmark")
    finally:
        services.DEFAULT_RESULTS_DIR = original_results_dir

    assert len(result["results"]) == 2
    models = sorted(row["model"] for row in result["results"])
    assert models == ["a", "b"]


def test_resolve_config_missing():
    with pytest.raises(services.EngineNotFound):
        services._resolve_config("/nonexistent/config.yaml")
