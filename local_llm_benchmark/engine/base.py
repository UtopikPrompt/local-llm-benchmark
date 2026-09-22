"""OpenAI-compatible request/response types and a base HTTP engine.

This module defines the canonical request/response shapes and a base class
that implements the OpenAI-compatible ``POST /v1/chat/completions`` endpoint.
Concrete engines subclass :class:`OpenAIEngine` and point it at their own
transport. See docs/adr/ADR-003-Engine-interface.md.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from local_llm_benchmark.errors import ConfigurationError, EngineError



@dataclass
class EngineConfig:
    """Connection parameters for a single engine instance."""

    endpoint: str
    api_key: Optional[str] = None
    timeout: float = 60.0
    model: str = ""


@dataclass
class StreamingToken:
    """A single streamed token plus its timing (ADR-007, ADR-011)."""

    token: str
    timestamp: float = field(default_factory=time.time)

    @property
    def delta(self) -> float:
        """Per-token latency in seconds since the previous token."""
        return self.timestamp - StreamingToken._previous_timestamp()

    @staticmethod
    def _previous_timestamp() -> float:
        # Not used directly; see :meth:`Engine.chat_stream`.
        return 0.0


class Engine(ABC):
    """Abstract base class for every LLM engine.

    Subclasses must implement :meth:`chat` and :meth:`chat_stream`. They
    translate the OpenAI-compatible request/response into engine-specific
    transport (httpx calls, subprocess, etc.).
    """

    #: Unique identifier, e.g. ``"vllm"``.
    name: str = ""
    #: Human-readable description shown in the UI.
    description: str = ""
    #: Set of capabilities this engine supports (e.g. ``{"streaming", "chat"}``).
    capabilities: set[str] = field(default_factory=set)

    def __init__(self, config: EngineConfig):
        if not config.endpoint:
            raise ConfigurationError("engine endpoint is required")
        self.config = config

    @property
    @abstractmethod
    def model(self) -> str:
        """The model name used for this engine."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        seed: int,
        temperature: float,
        max_tokens: int,
    ) -> "ChatCompletion":
        """Send a single chat completion request.

        :param messages: chat messages (system/user/assistant).
        :param seed: sampling seed for deterministic output (ADR-003).
        :param temperature: sampling temperature.
        :param max_tokens: maximum tokens to generate.
        """

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict],
        seed: int,
        temperature: float,
        max_tokens: int,
    ) -> Iterator["StreamingToken"]:
        """Yield tokens one at a time, streaming them (ADR-007).

        Each yielded :class:`StreamingToken` records the time it was produced
        so the storage layer can compute per-token latency and TTFT (ADR-011).
        """

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.__class__.__name__} name={self.name!r} model={self.model!r}>"


class ConfigurationError(Exception):
    """Raised when an engine configuration is invalid."""


class ChatCompletion:
    """A single chat completion response.

    Attributes mirror the OpenAI ``chat.completions`` response shape so the
    quality layer can consume any engine uniformly (ADR-003).
    """

    def __init__(
        self,
        model: str,
        messages: list[dict],
        seed: int,
        response: dict,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_duration: float = 0.0,
        engine: "Engine | None" = None,
    ):
        self.model = model
        self.messages = messages
        self.seed = seed
        self._response = response
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_duration = total_duration
        self.engine = engine

    @property
    def content(self) -> str:
        """The completion text, extracted from the engine's response."""
        try:
            return self._response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise EngineError(f"could not extract content from response: {self._response}")

    @property
    def finish_reason(self) -> Optional[str]:
        try:
            return self._response["choices"][0]["finish_reason"]
        except (KeyError, IndexError, TypeError):
            return None

    @property
    def raw(self) -> dict:
        """The raw engine response dict."""
        return self._response


class StreamingError(EngineError):
    """Raised when streaming fails midway."""


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
