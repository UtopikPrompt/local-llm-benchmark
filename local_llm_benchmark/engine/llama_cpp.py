"""llama.cpp engine plugin (openai_server mode).

llama.cpp can run ``openai_server.py`` which exposes an OpenAI-compatible
``POST /v1/chat/completions`` endpoint. This engine sends seeded sampling
requests (ADR-003).

Optional, additive plugin (ADR-003). Install with
``pip install local-llm-benchmark[llama-cpp]``.
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


class LlamaCppEngine(OpenAIEngine):
    """llama.cpp ``openai_server`` engine using the OpenAI-compatible API."""

    name = "llama-cpp"
    description = "llama.cpp openai_server"
    capabilities = {"streaming", "chat"}

    def __init__(self, config: EngineConfig):
        if not httpx:
            raise ConfigurationError(
                "llama-cpp engine requires httpx: pip install local-llm-benchmark[llama-cpp]"
            )
        super().__init__(config)

    @property
    def model(self) -> str:
        return self.config.model or "any-model"

    def _send(self, request: ChatRequest) -> ChatResponse:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        payload = {
            "model": request.model,
            "messages": request.messages,
            "seed": request.seed,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
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
            raise EngineError(f"llama.cpp returned {exc.response.status_code}: {exc}") from exc

    def _stream(self, request: ChatRequest) -> Iterator[StreamingToken]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        payload = {
            "model": request.model,
            "messages": request.messages,
            "seed": request.seed,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
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
                    choice = chunk.get("choices", [{}])[0]
                    delta = choice.get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield StreamingToken(token=content)
                        StreamingToken._previous_timestamp() = 0.0
        except httpx.HTTPStatusError as exc:
            raise EngineError(f"llama.cpp streaming failed: {exc}") from exc
