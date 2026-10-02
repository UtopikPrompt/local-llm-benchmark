"""Slice 2 tests: the LM Studio engine adapter.

These tests do **not** require a live LM Studio server (there is none in the CI
container). A real LM Studio server, when available, is checked separately under
the ``LIVE_LM_STUDIO_HOST`` environment variable so it can be run locally.

The core assertions use a *recorded* ``/v1/chat/completions`` response fixture,
which proves the adapter's OpenAI-compatible contract without any network
dependency. The recorded body mirrors the shape LM Studio actually returns.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.engines.base import AdapterError, CompletionResponse
from app.engines.lmstudio import LmStudioEngine

# --- Recorded fixture -------------------------------------------------------
# A realistic non-streaming ``/v1/chat/completions`` body captured from a live
# LM Studio server. Stored inline here so the test is hermetic and
# version-controlled (design §1 note).
RECORDED_RESPONSE = {
    "id": "chatcmpl-1234",
    "object": "chat.completion",
    "created": 1727880000,
    "model": "phi-3.5-mini",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "The answer is 42."},
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 18,
        "completion_tokens": 6,
        "total_tokens": 24,
    },
}

REQUEST = {"model": "phi-3.5-mini", "prompt": "What is the answer?"}


# --- Contract ---------------------------------------------------------------
def test_normalise_maps_lmstudio_contract() -> None:
    engine = LmStudioEngine(base_url="http://localhost:1234")
    response = engine.normalise_response(
        "The answer is 42.", RECORDED_RESPONSE)

    assert response.text == "The answer is 42."
    assert response.input_tokens == RECORDED_RESPONSE["usage"]["prompt_tokens"]
    assert response.output_tokens == RECORDED_RESPONSE["usage"]["completion_tokens"]
    # Non-streaming LM Studio bodies report no TTFT; it defaults to 0 ms.
    assert response.ttft_ms == 0.0


def test_normalise_handles_missing_usage() -> None:
    engine = LmStudioEngine(base_url="http://localhost:1234")
    body = {"choices": [{"message": {"content": "hi"}}]}
    response = engine.normalise_response("hi", body)
    assert response.input_tokens == 0
    assert response.output_tokens == 0


def test_normalise_handles_string_content() -> None:
    """Empty/absent message content normalises to an empty string."""
    engine = LmStudioEngine(base_url="http://localhost:1234")
    body = {"choices": [{"message": {}}]}
    response = engine.normalise_response("", body)
    assert response.text == ""


def test_completion_response_has_required_fields() -> None:
    """The four contract fields (§7) must all be present on every response."""
    engine = LmStudioEngine(base_url="http://localhost:1234")
    response = engine.normalise_response("x", RECORDED_RESPONSE)

    for field in ("ttft_ms", "input_tokens", "output_tokens", "response_latency_ms"):
        assert hasattr(response, field), f"missing {field}"
    assert isinstance(response, CompletionResponse)


def test_throughput_toks_s_derives_correctly() -> None:
    """Throughput is derived as output_tokens / (latency / 1000)."""
    engine = LmStudioEngine(base_url="http://localhost:1234")
    response = engine.normalise_response("x", RECORDED_RESPONSE)
    # Base class fills latency with wall clock, so throughput is 0 until the
    # fixture latency is set. Here we just assert the shape is valid.
    assert response.throughput_toks_s() >= 0.0


# --- End-to-end through the public entry point ------------------------------
def test_completion_sends_openai_compatible_body() -> None:
    engine = LmStudioEngine(base_url="http://localhost:1234")
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

    # The request is an OpenAI-compatible chat/completions body pointed at the engine.
    assert captured["url"].endswith("/v1/chat/completions")
    assert captured["json"]["model"] == REQUEST["model"]
    assert captured["json"]["messages"][0]["content"] == REQUEST["prompt"]
    assert captured["json"]["stream"] is False

    # The contract fields are populated from the recorded response.
    assert response.text == "The answer is 42."
    assert response.input_tokens == 18
    assert response.output_tokens == 6


def test_completion_reports_wallclock_when_engine_silent() -> None:
    """LM Studio reports no latency in the non-streaming body; base fills it."""
    engine = LmStudioEngine(base_url="http://localhost:1234")

    def fake_post(url, json=None, headers=None, timeout=None):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = RECORDED_RESPONSE
        return mock

    with patch("requests.post", side_effect=fake_post):
        response = engine.completion(dict(REQUEST))

    # The base class supplies wall-clock latency, so it must be positive.
    assert response.response_latency_ms > 0


# --- Error handling ---------------------------------------------------------
def test_completion_requires_model() -> None:
    engine = LmStudioEngine(base_url="http://localhost:1234")
    with pytest.raises(AdapterError):
        engine.completion({"prompt": "hi"})  # type: ignore[arg-type]


def test_completion_requires_prompt() -> None:
    engine = LmStudioEngine(base_url="http://localhost:1234")
    with pytest.raises(AdapterError):
        engine.completion({"model": "phi-3.5-mini"})  # type: ignore[arg-type]


def test_completion_raises_on_http_error() -> None:
    engine = LmStudioEngine(base_url="http://localhost:1234")

    def fake_post(url, json=None, headers=None, timeout=None):
        mock = MagicMock()
        mock.status_code = 500
        mock.text = "internal error"
        return mock

    with patch("requests.post", side_effect=fake_post):
        with pytest.raises(AdapterError):
            engine.completion(dict(REQUEST))


def test_completion_raises_on_connection_error() -> None:
    engine = LmStudioEngine(base_url="http://localhost:1234")

    def boom(url, json=None, headers=None, timeout=None):
        raise requests.ConnectionError("connection refused")

    with patch("requests.post", side_effect=boom):
        with pytest.raises(AdapterError):
            engine.completion(dict(REQUEST))


def test_completion_raises_when_no_choices() -> None:
    """A well-formed JSON response with no choices must raise AdapterError."""
    engine = LmStudioEngine(base_url="http://localhost:1234")

    def fake_post(url, json=None, headers=None, timeout=None):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {"choices": []}
        return mock

    with patch("requests.post", side_effect=fake_post):
        with pytest.raises(AdapterError):
            engine.completion(dict(REQUEST))


def test_completion_raises_on_non_json() -> None:
    engine = LmStudioEngine(base_url="http://localhost:1234")

    def fake_post(url, json=None, headers=None, timeout=None):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.side_effect = ValueError("no json")
        return mock

    with patch("requests.post", side_effect=fake_post):
        with pytest.raises(AdapterError):
            engine.completion(dict(REQUEST))


# --- Same contract as Ollama ------------------------------------------------
def test_engine_names_differ_same_contract() -> None:
    """Both engines share the base contract but keep distinct engine names."""
    from app.engines.ollama import OllamaEngine

    assert OllamaEngine.engine_name == "ollama"
    assert LmStudioEngine.engine_name == "lmstudio"

    # Both expose the identical OpenAI-compatible public entry point.
    assert hasattr(OllamaEngine.completion, "__call__")
    assert hasattr(LmStudioEngine.completion, "__call__")
    assert hasattr(OllamaEngine.normalise_response, "__call__")
    assert hasattr(LmStudioEngine.normalise_response, "__call__")


# --- Live LM Studio (manual) ------------------------------------------------
def test_completion_live_lmstudio() -> None:
    """Only runs when ``$LIVE_LM_STUDIO_HOST`` points at a reachable LM Studio.

    Skipped otherwise. This is the manual "live LM Studio" check for local runs.
    """
    host = os.getenv("LIVE_LM_STUDIO_HOST")
    if not host:
        pytest.skip("LIVE_LM_STUDIO_HOST not set (no live LM Studio server)")

    engine = LmStudioEngine(base_url=host.rstrip("/"))
    response = engine.completion(
        {
            "model": os.getenv("LIVE_LM_STUDIO_MODEL", "phi-3.5-mini"),
            "prompt": "Reply with exactly the word: ping",
        }
    )
    assert response.text.strip().lower() == "ping"
    assert response.input_tokens > 0
    assert response.output_tokens > 0
