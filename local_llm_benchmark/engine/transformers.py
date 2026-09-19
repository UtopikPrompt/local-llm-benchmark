"""HuggingFace Transformers engine plugin.

Uses HuggingFace Transformers' OpenAI-compatible interface
(``from transformers import OpenAIWrapper``). This engine can run locally
(with a model on disk) or against any OpenAI-compatible server (ADR-003).

Optional, additive plugin (ADR-003). Install with
``pip install local-llm-benchmark[transformers]``.
"""

from __future__ import annotations

import time
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
    from transformers import OpenAIWrapper
except ImportError:  # pragma: no cover
    OpenAIWrapper = None  # type: ignore


class TransformersEngine(OpenAIEngine):
    """HuggingFace Transformers ``OpenAIWrapper`` engine."""

    name = "transformers"
    description = "HuggingFace Transformers OpenAIWrapper"
    capabilities = {"streaming", "chat"}

    def __init__(self, config: EngineConfig):
        if not OpenAIWrapper:
            raise ConfigurationError(
                "transformers engine requires transformers: "
                "pip install local-llm-benchmark[transformers]"
            )
        super().__init__(config)

    @property
    def model(self) -> str:
        return self.config.model or "any-model"

    def _client(self) -> OpenAIWrapper:
        if self.config.api_key:
            return OpenAIWrapper(model=self.model, api_key=self.config.api_key)
        return OpenAIWrapper(model=self.model)

    def _send(self, request: ChatRequest) -> ChatResponse:
        client = self._client()
        try:
            response = client.chat.completions.create(
                messages=request.messages,
                seed=request.seed,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise EngineError(f"transformers failed: {exc}") from exc
        return ChatResponse(
            id=getattr(response, "id", ""),
            choices=[
                {"index": 0, "message": {"role": "assistant", "content": getattr(response, "choices", [{}])[0].get("message", {}).get("content", "")}, "finish_reason": getattr(response, "choices", [{}])[0].get("finish_reason")}
            ],
            usage={"prompt_tokens": getattr(response, "usage", None) and response.usage.prompt_tokens or 0, "completion_tokens": getattr(response, "usage", None) and response.usage.completion_tokens or 0},
            model=getattr(response, "model", self.model),
        )

    def _stream(self, request: ChatRequest) -> Iterator[StreamingToken]:
        client = self._client()
        try:
            response = client.chat.completions.create(
                messages=request.messages,
                seed=request.seed,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise EngineError(f"transformers streaming failed: {exc}") from exc
        last = 0.0
        for chunk in response:
            try:
                delta = chunk.choices[0].delta.content
            except (IndexError, AttributeError):
                continue
            if delta:
                yield StreamingToken(token=delta, timestamp=time.time())
                last = time.time()
