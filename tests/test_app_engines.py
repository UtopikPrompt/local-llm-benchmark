"""Tests that the dashboard can select among multiple configured engines.

Verifies the ``GET /engines`` endpoint exposes the configured engines and
that ``POST /run`` selects the chosen engine from the multi-engine config
instead of building a fresh single-engine config.
"""

from unittest.mock import AsyncMock, patch

import pytest

from fastapi.testclient import TestClient

from local_llm_benchmark.config import EngineConfig, BenchmarkConfig, load_config, write_config
from local_llm_benchmark.ui.app import create_app


@pytest.fixture()
def client(tmp_path):
    """Create an app whose Defaults has two configured engines.

    Engines are loaded from a config file on disk via ``create_app``'s
    ``config_path`` argument, exercising the real config-loading path instead
    of monkeypatching ``Defaults.engines``.
    """
    engines = [
        EngineConfig(name="ollama", base_url="http://host-a:11434", model="llama3"),
        EngineConfig(name="ollama-b", base_url="http://host-b:11434", model="llama3.1"),
    ]
    config_file = tmp_path / "config.yaml"
    config = BenchmarkConfig.from_dict({"engines": [e.to_dict() for e in engines]})
    write_config(config, config_file)
    return TestClient(create_app(config_path=config_file))


def test_get_engines_returns_configured_engines(client):
    """/engines must return the configured engines as a list of dicts."""
    resp = client.get("/engines")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload == [
        {"name": "ollama", "base_url": "http://host-a:11434", "model": "llama3", "timeout": 60.0, "max_concurrent": 1},
        {"name": "ollama-b", "base_url": "http://host-b:11434", "model": "llama3.1", "timeout": 60.0, "max_concurrent": 1},
    ]


def test_run_selects_configured_engine(client):
    """POST /run with an engine name must use that configured engine."""
    with patch("local_llm_benchmark.ui.app.run_benchmark", new=AsyncMock()) as rb:
        resp = client.post("/run", json={"engine": "ollama-b", "trials": 3})
        assert resp.status_code == 200
        engine = rb.call_args.args[0].engines[0]
        assert engine.name == "ollama-b"
        assert engine.base_url == "http://host-b:11434"
        assert engine.model == "llama3.1"


def test_run_unknown_engine_returns_404(client):
    """POST /run with an unknown engine name must fail with 404."""
    with patch("local_llm_benchmark.ui.app.run_benchmark", new=AsyncMock()) as rb:
        resp = client.post("/run", json={"engine": "nope"})
        assert resp.status_code == 404
        assert rb.call_count == 0


def test_run_without_engine_still_builds_single_engine(client):
    """POST /run without an engine selection still builds a single engine."""
    with patch("local_llm_benchmark.ui.app.run_benchmark", new=AsyncMock()) as rb:
        resp = client.post("/run", json={"base_url": "http://x:11434", "model": "m"})
        assert resp.status_code == 200
        engine = rb.call_args.args[0].engines[0]
        assert engine.base_url == "http://x:11434"
        assert engine.name == "ollama"


def test_create_app_loads_engines_from_config(tmp_path):
    """create_app must load the configured engines from the config file."""
    engines = [
        EngineConfig(name="ollama", base_url="http://host-a:11434", model="llama3"),
        EngineConfig(name="ollama-b", base_url="http://host-b:11434", model="llama3.1"),
    ]
    config_file = tmp_path / "config.yaml"
    config = BenchmarkConfig.from_dict({"engines": [e.to_dict() for e in engines]})
    write_config(config, config_file)

    # No live client: verify create_app populates the shared Defaults.engines.
    from local_llm_benchmark.config import Defaults

    create_app(config_path=config_file)
    assert Defaults.engines == engines
    assert Defaults.engines[0].to_dict() == {
        "name": "ollama",
        "base_url": "http://host-a:11434",
        "model": "llama3",
        "timeout": 60.0,
        "max_concurrent": 1,
    }


def test_create_app_defaults_to_project_config(tmp_path, monkeypatch):
    """create_app with no config_path auto-loads the project config.yaml."""
    engines = [EngineConfig(name="ollama", base_url="http://host-a:11434", model="llama3")]
    # Redirect the module's _CONFIG_FILE to the temp project config.
    monkeypatch.setattr("local_llm_benchmark.ui.app._CONFIG_FILE", tmp_path / "config.yaml")
    write_config(BenchmarkConfig.from_dict({"engines": [e.to_dict() for e in engines]}), tmp_path / "config.yaml")

    from local_llm_benchmark.config import Defaults

    create_app()
    assert Defaults.engines == engines
