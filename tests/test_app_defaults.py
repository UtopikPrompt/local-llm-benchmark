"""Tests that the web UI sources its form defaults from the server.

Verifies ``GET /defaults`` returns the centralized default values so the
dashboard form is populated on load and survives a page reload.
"""

import pytest

import pytest

from fastapi.testclient import TestClient

from local_llm_benchmark.config import (
    DEFAULT_ENGINE_BASE_URL,
    DEFAULT_ENGINE_MODEL,
    DEFAULT_JUDGE_BASE_URL,
    DEFAULT_JUDGE_MODEL,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_TIMEOUT,
    DEFAULT_OUTPUT,
    DEFAULT_FORMAT,
    DEFAULT_TASKS,
    DEFAULT_TRIALS,
)
from local_llm_benchmark.config import Defaults
from local_llm_benchmark.web.app import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_get_defaults_returns_expected_mapping(client):
    """/defaults must return the centralized defaults as a flat mapping."""
    resp = client.get("/defaults")
    assert resp.status_code == 200

    payload = resp.json()
    defaults = Defaults().to_dict()
    assert payload == defaults

    # Spot-check a few key values against the centralized constants.
    assert payload["engine_base_url"] == DEFAULT_ENGINE_BASE_URL
    assert payload["engine_model"] == DEFAULT_ENGINE_MODEL
    assert payload["judge_base_url"] == DEFAULT_JUDGE_BASE_URL
    assert payload["judge_model"] == DEFAULT_JUDGE_MODEL
    assert payload["timeout"] == DEFAULT_TIMEOUT
    assert payload["max_concurrent"] == DEFAULT_MAX_CONCURRENT
    assert payload["format"] == DEFAULT_FORMAT
    assert payload["tasks"] == DEFAULT_TASKS
    assert payload["output"] == DEFAULT_OUTPUT
    assert payload["trials"] == DEFAULT_TRIALS
    assert payload["task"] is None


def test_get_defaults_is_idempotent(client):
    """Re-fetching /defaults must return the same values (reload-safe)."""
    first = client.get("/defaults").json()
    second = client.get("/defaults").json()
    assert first == second
