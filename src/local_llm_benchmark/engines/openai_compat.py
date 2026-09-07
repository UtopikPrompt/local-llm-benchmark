"""OpenAI-compatible engine backend backed by :mod:`httpx`.

Talks to any server exposing an OpenAI-compatible chat-completions API, such
as Ollama (``http://host:11434``) or LM Studio. All network I/O is async and
streaming so the benchmark can measure true throughput without the local GIL
limiting it.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, List, Optional

import httpx

from local_llm_benchmark.config import EngineConfig
from local_llm_benchmark.engines.base import Engine


class EngineError(RuntimeError):
    """Raised when the engine fails to answer a request."""


def _build_url(base_url: str, path: str) -> str:
    """Append *path* to *base_url*, avoiding duplicate slashes."""
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _strip_usage_response(data: dict) -> dict:
    """Return the ``choices[0].message`` from an OpenAI completion payload."""
    return data.get("choices", [{}])[0].get("message", {})


def _stream_tokens(data: dict, stop: Optional[str]) -> AsyncIterator[str]:
    """Yield tokens from a streaming OpenAI response."""
    for chunk in data:
        if not isinstance(chunk, dict):
            continue
        content = chunk.get("choices", [{}])[0].get("delta") or {}
        token = content.get("content")
        if token:
            yield token
    if stop is not None:
        yield stop


class OpenAICompatEngine(Engine):
    """An engine that speaks the OpenAI chat-completions protocol."""

    def __init__(self, engine: EngineConfig) -> None:
        self.config = engine
        self._client: Optional[httpx.AsyncClient] = None
        self._model: Optional[str] = None

    async def _client(self) -> httpx.AsyncClient:
        """Return a lazily-created async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: List[dict],
        *,
        max_tokens: int,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Stream tokens from the remote engine.

        Graceful degradation: a server that is down, that lacks the
        ``/v1/models`` endpoint, or that streams a broken payload is treated as
        an empty list / no-op rather than raising.
        """
        try:
            client = await self._client()
            payload: dict[str, Any] = {
                "model": self._model or self.config.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "stream": stream,
            }
            response = await client.post(
                _build_url(self.config.base_url, "v1/chat/completions"),
                json=payload,
            )
            response.raise_for_status()
            if stream:
                async for token in _stream_tokens(response.iter_lines(), stop=None):
                    yield token
            else:
                data = response.json()
                yield _strip_usage_response(data).get("content", "") or ""
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError):
            # Graceful degradation: a missing endpoint or a bad stream must not
            # crash the benchmark. Yield nothing and return normally.
            return

    async def chat_completed(
        self,
        messages: List[dict],
        *,
        max_tokens: int,
    ) -> str:
        """Return a single non-streaming completion."""
        tokens = []
        async for token in self.chat(messages, max_tokens=max_tokens, stream=False):
            tokens.append(token)
        return "".join(tokens)

    async def list_models(self) -> List[str]:
        """List models served by the engine.

        Graceful degradation: a server missing ``/v1/models`` returns an empty
        list rather than raising.
        """
        try:
            client = await self._client()
            response = await client.get(_build_url(self.config.base_url, "v1/models"))
            if response.status_code != 200:
                return []
            data = response.json()
            models = data.get("data", [])
            return [model.get("id", "") for model in models if model.get("id")]
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, ValueError):
            return []

    async def models_available(self) -> bool:
        """Return ``True`` if the engine exposes a ``/v1/models`` endpoint."""
        try:
            client = await self._client()
            response = await client.get(_build_url(self.config.base_url, "v1/models"))
            return response.status_code == 200
        except httpx.RequestError:
            return False

    async def serve(self, engine: EngineConfig) -> None:
        """Serve the engine as an OpenAI-compatible proxy until stopped.

        This is the engine's *compute* role; the benchmark never calls it.
        """
        from local_llm_benchmark.ui.proxy import serve_proxy

        await serve_proxy(engine)

    async def unload_model(self) -> None:
        """Unload the currently loaded model from memory."""
        # Ollama / LM Studio are remote; there is nothing to unload locally.
        await self.close()
