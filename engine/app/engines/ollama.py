"""Ollama engine adapter (design §9, contract 1).

Talks to an Ollama server over its OpenAI-compatible
``/api/chat`` stream endpoint. Ollama already returns the OpenAI-shaped body we
need, so this adapter mostly forwards requests and normalises the streamed
response into the unified :class:`CompletionResponse` contract.

Points at ``$OLLAMA_BASE_URL`` (default ``http://localhost:11434``); see
``app.core.config``.
"""

from __future__ import annotations

import json
import time

import requests

from app.engines.base import AdapterError, CompletionResponse, EngineAdapter


def _text_from_message(message: dict) -> str:
    """Extract the text content from a chat message dict."""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # multimodal payload, keep it simple
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return " ".join(parts)
    return ""


class OllamaEngine(EngineAdapter):
    """Engine adapter for a running Ollama server.

    Implements the unified OpenAI-compatible contract. A real Ollama endpoint is
    not expected inside the CI container, so tests exercise this adapter against
    a recorded fixture rather than a live server (see
    ``tests/test_ollama_engine.py``).
    """

    engine_name = "ollama"
    """Canonical engine name, used in stored runs (design §7)."""

    def _completion_url(self) -> str:
        return f"{self.base_url}/api/chat"

    def _build_payload(self, payload: dict) -> dict:
        """Translate the benchmark request into an ``/api/chat`` body.

        Ollama uses ``messages`` rather than a single ``prompt``; we build a
        single ``user`` message from the request while forwarding any engine
        options (temperature, num_predict, etc.) as ``stream_options``.
        """
        ollama_payload: dict = {
            "model": payload["model"],
            "messages": [{"role": "user", "content": payload["prompt"]}],
            "stream": False,
        }
        # Forward Ollama-native options under ``options`` if present.
        for key in (
            "temperature",
            "top_p",
            "num_predict",
            "seed",
            "options",
        ):
            if key in payload:
                ollama_payload[key] = payload[key]
        return ollama_payload

    def _do_completion(self, payload: dict) -> CompletionResponse:
        body = self._build_payload(payload)
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(
                self._completion_url(),
                json=body,
                headers=headers,
                timeout=120,
            )
        except requests.RequestException as exc:
            raise AdapterError(
                f"Ollama request to {self.base_url} failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise AdapterError(
                f"Ollama returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise AdapterError(
                "Ollama returned a non-JSON response"
            ) from exc

        if not isinstance(data, dict):
            raise AdapterError("Ollama response is not a JSON object")

        text = _text_from_message(data.get("message") or {})
        return self.normalise_response(text, data)

    def normalise_response(self, text: str, data: dict) -> CompletionResponse:
        """Map Ollama's ``/api/chat`` response to the completion contract.

        Ollama reports durations in nanoseconds; we convert every field to
        milliseconds (divide by 1e6) so the response matches the contract.
        ``total_duration`` is the generation time (prompt eval + decode + load),
        which we expose as both the time-to-first-token proxy and the response
        latency so the base class can guard against timing bugs.
        """
        ttft = float(data.get("total_duration", 0) / 1_000_000)
        input_tokens = int(data.get("prompt_eval_count", 0))
        output_tokens = int(data.get("eval_count", 0))
        thinking_ms = 0.0
        if data.get("eval_duration"):
            thinking_ms = data["eval_duration"] / 1_000_000.0
        response_latency_ms = float(data.get("total_duration", 0) / 1_000_000)
        return CompletionResponse(
            text=text,
            ttft_ms=ttft,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_latency_ms=response_latency_ms,
            thinking_time_ms=thinking_ms,
        )
