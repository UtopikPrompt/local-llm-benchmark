"""Engine interface: the abstraction every engine implements.

Engines speak the OpenAI-compatible ``POST /v1/chat/completions`` interface
with seeded sampling (ADR-003). Each engine is an optional, additive plugin
never a hard dependency (ADR-003).

The :class:`Engine` base class defines the contract:
    * :meth:`Engine.chat`          -> single completion
    * :meth:`Engine.chat_stream`   -> streaming tokens for SSE (ADR-007)

Concrete engines (vLLM, llama.cpp, Ollama, HuggingFace Transformers) subclass
this and implement the HTTP transport. See docs/adr/ADR-003-Engine-interface.md.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional

from local_llm_benchmark.errors import EngineError

# Importing the concrete engines below registers them with the registry
# (ADR-003). Each engine self-registers on import.
from local_llm_benchmark.engine import (  # noqa: F401,E402
    llama_cpp,
    ollama,
    transformers,
    vllm,
)
from local_llm_benchmark.engine.registry import (  # noqa: F401,E402
    available_engines,
    engine_names,
    get_engine_class,
    register_engine,
)


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
