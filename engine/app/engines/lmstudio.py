"""LM Studio engine adapter (design §9, contract 1).

Talks to an LM Studio server over its OpenAI-compatible ``/v1/chat/completions``
endpoint. LM Studio speaks the OpenAI chat-completions API directly, so this
adapter forwards requests and normalises the ``choices`` + ``usage`` response
into the unified :class:`CompletionResponse` contract.

Points at ``$LM_STUDIO_BASE_URL`` (default ``http://localhost:1234``); see
``app.core.config``.
"""

from __future__ import annotations

import time

import requests

from app.engines.base import AdapterError, CompletionResponse, EngineAdapter


class LmStudioEngine(EngineAdapter):
    """Engine adapter for a running LM Studio server.

    Implements the unified OpenAI-compatible contract, identical to
    :class:`app.engines.ollama.OllamaEngine`. A real LM Studio endpoint is not
    expected inside the CI container, so tests exercise this adapter against a
    recorded fixture rather than a live server (see
    ``tests/test_lmstudio_engine.py``).
    """

    engine_name = "lmstudio"
    """Canonical engine name, used in stored runs (design §7)."""

    def _completion_url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    def _build_payload(self, payload: dict) -> dict:
        """Translate the benchmark request into an OpenAI ``chat/completions`` body.

        LM Studio uses ``messages`` rather than a single ``prompt``; we build a
        single ``user`` message from the request while forwarding any engine
        options (temperature, max_tokens, top_p, etc.).
        """
        lmstudio_payload: dict = {
            "model": payload["model"],
            "messages": [{"role": "user", "content": payload["prompt"]}],
            "stream": False,
        }
        # Forward OpenAI-native options if present on the request.
        for key in (
            "temperature",
            "top_p",
            "max_tokens",
            "seed",
            "n",
        ):
            if key in payload:
                lmstudio_payload[key] = payload[key]
        return lmstudio_payload

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
                f"LM Studio request to {self.base_url} failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise AdapterError(
                f"LM Studio returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise AdapterError(
                "LM Studio returned a non-JSON response"
            ) from exc

        if not isinstance(data, dict):
            raise AdapterError("LM Studio response is not a JSON object")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AdapterError("LM Studio response has no choices")

        message = choices[0].get("message") or {}
        text = message.get("content") or ""
        if not isinstance(text, str):
            text = ""
        return self.normalise_response(text, data)

    def normalise_response(self, text: str, data: dict) -> CompletionResponse:
        """Map LM Studio's ``/v1/chat/completions`` response to the contract.

        LM Studio reports token counts under ``usage``; TTFT is not part of the
        non-streaming body, so it defaults to ``0.0`` and the base class fills
        ``response_latency_ms`` with wall-clock timing.
        """
        usage = data.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens", 0))
        output_tokens = int(usage.get("completion_tokens", 0))
        return CompletionResponse(
            text=text,
            ttft_ms=0.0,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            # 0 signals the base class to use wall-clock latency.
            response_latency_ms=0.0,
        )
