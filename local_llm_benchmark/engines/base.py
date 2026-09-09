"""Abstract engine backend.

An :class:`Engine` talks to a remote OpenAI-compatible chat-completions API.
Concrete backends (e.g. :class:`~local_llm_benchmark.engines.openai_compat.OpenAICompatEngine`)
implement the :meth:`chat`, :meth:`chat_completed`, :meth:`list_models`,
:meth:`serve` and :meth:`unload_model` interface.

The benchmark never touches the engine's compute loop directly; it streams the
model's token responses over :meth:`chat` and measures throughput from there.
"""

from __future__ import annotations

import abc
from typing import AsyncIterator, List, Optional

from local_llm_benchmark.config import EngineConfig


class Engine(abc.ABC):
    """Abstract base class for all engine backends."""

    #: Whether this engine supports listing its models.
    supports_list_models: bool = True

    @abc.abstractmethod
    async def chat(
        self,
        messages: List[dict],
        *,
        max_tokens: int,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Stream the completion, yielding one token at a time.

        Args:
            messages: Chat messages in OpenAI format.
            max_tokens: Maximum tokens to generate.
            stream: If ``True`` yield tokens incrementally; otherwise yield a
                single final token.

        Yields:
            Generated tokens (without the ``stop`` token).
        """

    @abc.abstractmethod
    async def chat_completed(
        self,
        messages: List[dict],
        *,
        max_tokens: int,
    ) -> str:
        """Return a single non-streaming completion."""

    @abc.abstractmethod
    async def list_models(self) -> List[str]:
        """Return the list of models served by the engine."""

    @abc.abstractmethod
    async def serve(self, engine: EngineConfig) -> None:
        """Serve the engine as an OpenAI-compatible proxy until stopped."""

    @abc.abstractmethod
    async def unload_model(self) -> None:
        """Unload the currently loaded model from memory."""

    @staticmethod
    def build(engine: EngineConfig) -> Engine:
        """Return an engine instance for *engine*.

        Resolves the engine name to a concrete backend. The runner uses this to
        obtain the implementation without importing the engine module eagerly.
        """
        from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine

        return OpenAICompatEngine(engine)
