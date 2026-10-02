"""Slice 1 tests: the Ollama engine adapter.

These tests do **not** require a live Ollama server (there is none in the CI
container). A real Ollama server, when available, is checked separately under
the ``LIVE_OLLAMA_HOST`` environment variable so it can be run locally.

The core assertions use a *recorded* Ollama ``/api/chat`` response fixture, which
proves the adapter's OpenAI-compatible contract without any network dependency.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.engines.base import AdapterError, CompletionResponse
from app.engines.ollama import OllamaEngine

# --- Recorded fixture -------------------------------------------------------
# A realistic ``/api/chat`` body captured from a live Ollama server. Stored
# inline here so the test is hermetic and version-controlled (design §1 note).
RECORDED_RESPONSE = {
    "model": "phi-3.5-mini",
    "created_at": "2026-10-02T10:00:00Z",
    "message": {
        "role": "assistant",
        "content": "The answer is 42.",
    },
    "done": True,
    "prompt_eval_count": 18,
    "eval_count": 6,
    "total_duration": 1_500_000_000,      # ns -> 1.5 s
    "eval_duration": 900_000_000,        # ns -> 0.9 s
    "load_duration": 100_000_000,
}

REQUEST = {"model": "phi-3.5-mini", "prompt": "What is the answer?"}


# --- Contract contract ------------------------------------------------------
def test_normalise_maps_ollama_contract() -> None:
    engine = OllamaEngine(base_url="http://localhost:11434")
    response = engine.normalise_response(
        "The answer is 42.", RECORDED_RESPONSE)

    assert response.text == "The answer is 42."
    assert response.input_tokens == RECORDED_RESPONSE["prompt_eval_count"]
    assert response.output_tokens == RECORDED_RESPONSE["eval_count"]
    # Ollama durations are in nanoseconds; the contract fields are milliseconds.
    assert response.ttft_ms == pytest.approx(1500.0, rel=0.01)
    assert response.thinking_time_ms == pytest.approx(900.0, rel=0.01)


def test_completion_response_has_required_fields() -> None:
    """The four contract fields (§7) must all be present on every response."""
    engine = OllamaEngine(base_url="http://localhost:11434")
    response = engine.normalise_response("x", RECORDED_RESPONSE)

    for field in ("ttft_ms", "input_tokens", "output_tokens", "response_latency_ms"):
        assert hasattr(response, field), f"missing {field}"
    assert isinstance(response, CompletionResponse)


def test_throughput_toks_s_derives_correctly() -> None:
    engine = OllamaEngine(base_url="http://localhost:11434")
    response = engine.normalise_response("x", RECORDED_RESPONSE)
    # 6 tokens over 1.5 s.
    assert response.throughput_toks_s() == pytest.approx(4.0, rel=0.01)


# --- End-to-end through the public entry point ------------------------------
def test_completion_sends_openai_compatible_body() -> None:
    engine = OllamaEngine(base_url="http://localhost:11434")
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = RECORDED_RESPONSE
        return mock

    with patch("requests.post", side_effect=fake_post):
        response = engine.completion(dict(REQUEST))

    # The request is an OpenAI-compatible /api/chat body pointed at the engine.
    assert captured["url"].endswith("/api/chat")
    assert captured["json"]["model"] == REQUEST["model"]
    assert captured["json"]["messages"][0]["content"] == REQUEST["prompt"]
    assert captured["json"]["stream"] is False

    # The four contract fields are populated from the recorded response.
    assert response.text == "The answer is 42."
    assert response.input_tokens == 18
    assert response.output_tokens == 6
    assert response.response_latency_ms > 0


def test_completion_prefers_engine_latency_over_wallclock() -> None:
    """The base class never reports less than wall clock (timing-bug guard)."""
    engine = OllamaEngine(base_url="http://localhost:11434")
    fixture = dict(RECORDED_RESPONSE)
    fixture["total_duration"] = 3_000_000_000  # 3.0 s

    def fake_post(url, json=None, headers=None, timeout=None):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = fixture
        return mock

    with patch("requests.post", side_effect=fake_post):
        response = engine.completion(dict(REQUEST))

    # Engine reports 3.0 s (3000 ms); wall clock is far smaller. Base picks the larger.
    assert response.response_latency_ms == pytest.approx(3000.0, rel=0.01)


def test_completion_reports_wallclock_when_engine_silent() -> None:
    """When the engine reports 0 latency, base falls back to wall clock."""
    engine = OllamaEngine(base_url="http://localhost:11434")
    fixture = dict(RECORDED_RESPONSE)
    fixture["total_duration"] = 0

    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = fixture
        return mock

    with patch("requests.post", side_effect=fake_post):
        response = engine.completion(dict(REQUEST))

    assert response.response_latency_ms > 0


# --- Error handling ---------------------------------------------------------
def test_completion_requires_model() -> None:
    engine = OllamaEngine(base_url="http://localhost:11434")
    with pytest.raises(AdapterError):
        engine.completion({"prompt": "hi"})  # type: ignore[arg-type]


def test_completion_requires_prompt() -> None:
    engine = OllamaEngine(base_url="http://localhost:11434")
    with pytest.raises(AdapterError):
        engine.completion({"model": "phi-3.5-mini"})  # type: ignore[arg-type]


def test_completion_raises_on_http_error() -> None:
    engine = OllamaEngine(base_url="http://localhost:11434")

    def fake_post(url, json=None, headers=None, timeout=None):
        mock = MagicMock()
        mock.status_code = 500
        mock.text = "internal error"
        return mock

    with patch("requests.post", side_effect=fake_post):
        with pytest.raises(AdapterError):
            engine.completion(dict(REQUEST))


def test_completion_raises_on_connection_error() -> None:
    engine = OllamaEngine(base_url="http://localhost:11434")

    def boom(url, json=None, headers=None, timeout=None):
        raise requests.ConnectionError("connection refused")

    with patch("requests.post", side_effect=boom):
        with pytest.raises(AdapterError):
            engine.completion(dict(REQUEST))


# --- Live Ollama (manual) ---------------------------------------------------
def test_completion_live_ollama() -> None:
    """Only runs when ``$LIVE_OLLAMA_HOST`` points at a reachable Ollama server.

    Skipped otherwise. This is the manual "live Ollama" check for local runs.
    """
    host = os.getenv("LIVE_OLLAMA_HOST")
    if not host:
        pytest.skip("LIVE_OLLAMA_HOST not set (no live Ollama server)")

    engine = OllamaEngine(base_url=host.rstrip("/"))
    response = engine.completion(
        {
            "model": os.getenv("LIVE_OLLAMA_MODEL", "phi-3.5-mini"),
            "prompt": "Reply with exactly the word: ping",
        }
    )
    assert response.text.strip().lower() == "ping"
    assert response.input_tokens > 0
    assert response.output_tokens > 0
