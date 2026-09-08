"""Tests that the dashboard can select among multiple configured engines.

Verifies the ``GET /engines`` endpoint exposes the configured engines and
that ``POST /run`` selects the chosen engine from the multi-engine config
instead of building a fresh single-engine config.
"""

from unittest.mock import AsyncMock, patch

import pytest

from fastapi.testclient import TestClient

from local_llm_benchmark.config import EngineConfig
from local_llm_benchmark.ui.app import create_app


@pytest.fixture()
def client(monkeypatch):
    """Create an app whose Defaults has two configured engines."""
    monkeypatch.setattr(
        "local_llm_benchmark.ui.app.Defaults.engines",
        [
            EngineConfig(name="ollama", base_url="http://host-a:11434", model="llama3"),
            EngineConfig(name="ollama-b", base_url="http://host-b:11434", model="llama3.1"),
        ],
    )
    return TestClient(create_app())


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
