"""OpenAI-compatible request/response types and a base HTTP engine.

This module defines the canonical request/response shapes and a base class
that implements the OpenAI-compatible ``POST /v1/chat/completions`` endpoint.
Concrete engines subclass :class:`OpenAIEngine` and point it at their own
transport. See docs/adr/ADR-003-Engine-interface.md.
"""

from __future__ import annotations

import json
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from local_llm_benchmark.engine.base import (
    ChatCompletion,
    Engine,
    EngineConfig,
    StreamingError,
    StreamingToken,
)
from local_llm_benchmark.errors import ConfigurationError, EngineError


@dataclass
class ChatRequest:
    """OpenAI-compatible chat request (subset used by the benchmark)."""

    messages: list[dict]
    seed: int
    temperature: float
    max_tokens: int
    model: str = ""


@dataclass
class ChatResponse:
    """OpenAI-compatible chat completion response."""

    id: str = ""
    choices: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    model: str = ""
    system_fingerprint: Optional[str] = None


class OpenAIEngine(Engine):
    """Base engine implementing the OpenAI-compatible interface.

    Subclasses implement :meth:`_send` to perform the actual transport call.
    This base handles request shaping, seed injection, and response parsing so
    every engine behaves identically (ADR-003).
    """

    def __init__(self, config: EngineConfig):
        super().__init__(config)
        if not self.name:
            raise ConfigurationError("engine name is required")
        if not self.description:
            raise ConfigurationError("engine description is required")

    @property
    @abstractmethod
    def model(self) -> str:
        """The model name advertised to the engine."""

    @abstractmethod
    def _send(self, request: ChatRequest) -> ChatResponse:
        """Perform the transport call and return a parsed response."""

    def chat(self, messages, seed, temperature, max_tokens) -> ChatCompletion:
        request = ChatRequest(
            messages=list(messages),
            seed=seed,
            temperature=temperature,
            max_tokens=max_tokens,
            model=self.model,
        )
        response = self._send(request)
        choices = response.choices
        if not choices:
            raise EngineError("engine returned no choices")
        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content")
        if content is None:
            content = ""
        return ChatCompletion(
            model=response.model or self.model,
            messages=request.messages,
            seed=seed,
            response=choice,
            prompt_tokens=int(response.usage.get("prompt_tokens", 0)),
            completion_tokens=int(response.usage.get("completion_tokens", 0)),
            total_duration=choice.get("duration_ms", 0.0) / 1000.0,
            engine=self,
        )

    def chat_stream(self, messages, seed, temperature, max_tokens) -> Iterator[StreamingToken]:
        """Stream tokens via the OpenAI-compatible streaming API (ADR-007).

        The base implementation uses ``stream: true`` and yields each delta
        token, recording its timestamp for offline timing storage (ADR-011).
        """
        request = ChatRequest(
            messages=list(messages),
            seed=seed,
            temperature=temperature,
            max_tokens=max_tokens,
            model=self.model,
            stream=True,
        )
        try:
            yield from self._stream(request)
        except Exception as exc:  # noqa: BLE001
            raise StreamingError(str(exc)) from exc

    @abstractmethod
    def _stream(self, request: ChatRequest) -> Iterator[StreamingToken]:
        """Yield :class:`StreamingToken` objects for the request."""

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"<OpenAIEngine {self.name} {self.model}>"
