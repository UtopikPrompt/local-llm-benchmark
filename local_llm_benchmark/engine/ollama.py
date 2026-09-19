"""Ollama engine plugin.

Ollama exposes an OpenAI-compatible ``POST /v1/chat/completions`` endpoint.
This engine sends seeded sampling requests (ADR-003).

Optional, additive plugin (ADR-003). Install with
``pip install local-llm-benchmark[ollama]``.
"""

from __future__ import annotations

from typing import Iterator

from local_llm_benchmark.engine.base import (
    ChatRequest,
    ChatResponse,
    Engine,
    EngineConfig,
    OpenAIEngine,
    StreamingToken,
)
from local_llm_benchmark.errors import ConfigurationError, EngineError

try:  # pragma: no cover - optional dependency
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore


class OllamaEngine(OpenAIEngine):
    """Ollama engine using the OpenAI-compatible HTTP API."""

    name = "ollama"
    description = "Ollama server"
    capabilities = {"streaming", "chat"}

    def __init__(self, config: EngineConfig):
        if not httpx:
            raise ConfigurationError(
                "ollama engine requires httpx: pip install local-llm-benchmark[ollama]"
            )
        super().__init__(config)

    @property
    def model(self) -> str:
        return self.config.model or "llama3.3"

    def _send(self, request: ChatRequest) -> ChatResponse:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": request.model,
            "messages": request.messages,
            "seed": request.seed,
            "stream": False,
        }
        try:
            resp = httpx.post(
                f"{self.config.endpoint.rstrip('/')}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
            )
            resp.raise_for_status()
            return ChatResponse(**resp.json())
        except httpx.HTTPStatusError as exc:
            raise EngineError(f"ollama returned {exc.response.status_code}: {exc}") from exc

    def _stream(self, request: ChatRequest) -> Iterator[StreamingToken]:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": request.model,
            "messages": request.messages,
            "seed": request.seed,
            "stream": True,
        }
        try:
            with httpx.stream(
                "POST",
                f"{self.config.endpoint.rstrip('/')}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
            ) as stream:
                for line in stream.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = __import__("json").loads(data)
                    except (ValueError, TypeError):
                        continue
                    choice = chunk.get("message", {})
                    content = choice.get("content")
                    if content:
                        yield StreamingToken(token=content)
                        StreamingToken._previous_timestamp() = 0.0
        except httpx.HTTPStatusError as exc:
            raise EngineError(f"ollama streaming failed: {exc}") from exc
