"""Tests for the API service layer (business logic behind the endpoints).

The services contain no HTTP concern, so they are exercised directly without a
FastAPI client: a plain dict is posted as the request body and the result rows
are asserted on.
"""

from unittest.mock import AsyncMock, patch

import pytest

from local_llm_benchmark.config import BenchmarkConfig, Defaults, EngineConfig, JudgeConfig, load_config
from local_llm_benchmark.results import Row
from local_llm_benchmark.server.api import services


def _fake_rows():
    return [Row(engine="engine", model="model", task_id="qa", category="qa")]


def _fake_run(monkeypatch):
    """Patch the runner so ``run`` returns canned rows without network I/O."""
    import local_llm_benchmark.runner as runner

    monkeypatch.setattr(runner, "run_benchmark", AsyncMock(return_value=_fake_rows()))


async def test_run_selects_configured_engine(monkeypatch):
    config_file = monkeypatch.tmp_path / "config.yaml"
    config_file.write_text("engines:\n- name: ollama\n  base_url: http://a:11434\n  model: llama3\n")
    monkeypatch.setattr("local_llm_benchmark.config.project_config_path", lambda: config_file)

    _fake_run(monkeypatch)
    with patch("local_llm_benchmark.server.api.services.write_report") as wr:
        # Original: result = await services.run({"engine": "ollama", "trials": 3})
        result = services.run({"engine": "ollama", "trials": 3})

    assert result["rows"][0]["engine"] == "engine"
    # The report is written to the configured output path.
    wr.assert_called_once()
    assert wr.call_args.args[0] == result["output"]


def test_run_unknown_engine_raises(monkeypatch):
    _fake_run(monkeypatch)
    with patch("local_llm_benchmark.server.api.services.write_report") as wr:
        with pytest.raises(services.EngineNotFound):
            services.run({"engine": "nope"})
    wr.assert_not_called()


def test_run_missing_fields_raises(monkeypatch):
    _fake_run(monkeypatch)
    with patch("local_llm_benchmark.server.api.services.write_report") as wr:
        with pytest.raises(services.BadRequest):
            services.run({"model": "m"})
    with patch("local_llm_benchmark.server.api.services.write_report") as wr:
        with pytest.raises(services.BadRequest):
            services.run({"base_url": "http://x:1"})
    wr.assert_not_called()


def test_run_builds_single_engine(monkeypatch):
    _fake_run(monkeypatch)
    with patch("local_llm_benchmark.server.api.services.write_report"):
        services.run({"base_url": "http://x:11434", "model": "m"})


async def test_run_defaults_from_defaults(monkeypatch):
    """When no fields are given, the centralized Defaults seed a single engine."""
    Defaults.engines = []
    _fake_run(monkeypatch)
    with patch("local_llm_benchmark.server.api.services.write_report") as wr:
        await services.run({})

    # A single engine built from the defaults is constructed.
    config = wr.call_args.args[0]
    assert len(config.engines) == 1
    assert config.engines[0].base_url == "http://localhost:11434"
    assert config.engines[0].model == "llama3"


async def test_run_with_judge(monkeypatch):
    _fake_run(monkeypatch)
    with patch("local_llm_benchmark.server.api.services.write_report"):
        await services.run({"base_url": "http://x:1", "model": "m", "judge_url": "http://judge:1"})


async def test_defaults_endpoint():
    result = await services.defaults()
    assert result["engine_base_url"] == "http://localhost:11434"
    assert result["trials"] == 3


async def test_engines_endpoint(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "engines:\n"
        "- name: ollama\n  base_url: http://a:11434\n  model: llama3\n"
        "- name: ollama-b\n  base_url: http://b:11434\n  model: llama3.1\n"
    )
    monkeypatch.setattr("local_llm_benchmark.config.project_config_path", lambda: config_file)
    engines = await services.engines()
    assert [e["name"] for e in engines] == ["ollama", "ollama-b"]


async def test_engines_endpoint_missing_config(tmp_path, monkeypatch):
    monkeypatch.setattr("local_llm_benchmark.config.project_config_path", lambda: tmp_path / "nope.yaml")
    assert await services.engines() == []


async def test_engines_endpoint_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("local_llm_benchmark.config.project_config_path", lambda: tmp_path / "nope.yaml")
    with pytest.raises(services.EngineNotFound):
        await services.engines()


def test_new_engine_from_request_defaults():
    defaults = Defaults()
    engine = services._new_engine_from_request({"base_url": "http://x:1", "model": "m"}, defaults)
    assert engine.name == "ollama"
    assert engine.base_url == "http://x:1"
    assert engine.model == "m"


def test_new_judge_from_request():
    defaults = Defaults()
    judge = services._new_judge_from_request({"judge_url": "http://j:1", "model": "m"}, defaults)
    assert judge is not None
    assert judge.base_url == "http://j:1"
    assert judge.name == "judge"
    # The alternate spelling ``judgeUrl`` is also accepted.
    assert services._new_judge_from_request({"judgeUrl": "http://j2:1"}, defaults) is not None
    # Without a judge URL, no judge is built.
    assert services._new_judge_from_request({}, defaults) is None


def test_engines_loads_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("engines:\n- name: ollama\n  base_url: http://a:11434\n  model: llama3\n")
    engines = [e.to_dict() for e in load_config(config_file).engines]
    assert engines == [{"name": "ollama", "base_url": "http://a:11434", "model": "llama3"}]
