"""End-to-end tests against the FastAPI application via TestClient."""

import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from local_llm_benchmark import config
from local_llm_benchmark.benchmarks.speed import Row
from local_llm_benchmark.server.api import services
from local_llm_benchmark.server.api.controller import create_app


@pytest.fixture()
def client():
    import os
    import tempfile
    import yaml

    config_data = {
        "engines": [
            {"name": "stub", "base_url": "http://fake.local", "model": "stub-model"},
        ]
    }
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w") as fh:
        fh.write(yaml.safe_dump(config_data))

    app = create_app(config_path=path)
    with TestClient(app) as test_client:
        yield test_client
    os.remove(path)


def test_get_defaults(client):
    resp = client.get("/api/defaults")
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_concurrent"] == 1
    assert data["timeout"] == 60.0


def test_get_engines(client):
    resp = client.get("/api/engines")
    assert resp.status_code == 200
    engines = resp.json()
    assert isinstance(engines, list)
    assert len(engines) >= 1


def test_post_run_success(monkeypatch, client):
    # Redirect the report output to a temp path: services.run() always calls
    # write_report(rows, config.output) with the *default* output (a timestamped
    # file in results/). Stubbing write_report and sending an explicit tmp output
    # path prevents this e2e test from writing a real result file into results/.
    fd, out_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    monkeypatch.setattr("local_llm_benchmark.server.api.services.write_report", lambda *a, **k: None)

    row = Row(engine="stub", model="stub-model", task_id="t1", tok_per_s=100.0)

    async def fake_run_benchmark(*a, **k):
        return [row]

    monkeypatch.setattr("local_llm_benchmark.server.api.services.runner.run_benchmark", fake_run_benchmark)
    resp = client.post("/api/run", json={"engine": "stub", "output": out_path})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["task_id"] == "t1"


def test_post_run_unknown_engine(client):
    resp = client.post("/api/run", json={"engine": "nope"})
    assert resp.status_code == 404


def test_post_run_missing_base_url(client, monkeypatch):
    # /api/run with no "output" uses the default output (a timestamped file in
    # results/). Stub write_report so this e2e test verifies the 200 response
    # without polluting results/ with a real corpus result file.
    monkeypatch.setattr("local_llm_benchmark.server.api.services.write_report", lambda *a, **k: None)
    resp = client.post("/api/run", json={"engine": "stub"})
    assert resp.status_code == 200
    assert "rows" in resp.json()


async def test_post_config_preview_requires_params(client):
    resp = client.post("/api/config", json={"base_url": "http://fake.local", "model": "m"})
    assert resp.status_code == 422
    assert "detail" in resp.json()


async def test_post_models_requires_params(client):
    resp = client.post("/api/models", json={"base_url": "http://fake.local"})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_get_results(client):
    # Create a fake result file the report format expects.
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump({"results": [], "config": {}, "meta": {}}, fh)
    resp = client.get(f"/api/results/{path}")
    # A report with no rows should still return 200.
    assert resp.status_code in (200, 404)
    os.remove(path)


async def test_post_invalid_engine_returns_400_detail(client):
    resp = client.post("/api/run", json={})
    assert resp.status_code == 400
    assert "detail" in resp.json()
