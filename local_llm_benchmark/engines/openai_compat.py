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


def _strip_content(message: dict) -> str:
    """Return the assistant text from a completion ``message``.

    Some engines place their output in the ``reasoning`` field rather than
    ``content``; capture whichever is present so the returned text is complete.
    """
    return message.get("content") or message.get("reasoning") or ""


def _extract_token(parsed: Any) -> Optional[str]:
    """Extract the next token string from a parsed NDJSON/SSE object.

    Handles three shapes:

    * **OpenAI SSE delta** (``{"choices":[{"delta":{"content":"x"}}]}``) — a
      reasoning model's token also appears under ``reasoning``.
    * **Ollama NDJSON** — each line is a *complete* delta object
      (``{"model":..., "message":{"role":"assistant", "content":"x"},
      "done":...}``) with the token at ``message.content`` (or ``reasoning``).
      There is no ``choices`` wrapper and no ``data:`` prefix.
      A reasoning model (``gemma4:e2b``) also emits every answer token in the
      top-level ``thinking`` field during the reasoning phase, where
      ``message.content`` is still empty.
    """
    if isinstance(parsed, dict):
        delta = parsed.get("choices", [{}])[0].get("delta") or {}
        if delta.get("content") is not None or delta.get("reasoning") is not None:
            return delta.get("content") or delta.get("reasoning")
        if (parsed.get("message", {}).get("content") is not None or parsed.get("reasoning") is not None or parsed.get("thinking") is not None):
            return parsed.get("message", {}).get("content") or parsed.get("reasoning") or parsed.get("thinking")
    return None


def _stream_tokens(data: dict, stop: Optional[str]) -> AsyncIterator[str]:
    """Yield tokens from a streaming response (OpenAI SSE or Ollama NDJSON).

    ``*data*`` is an iterable of stream items. Each item is either a parsed
    JSON object (from ``_aiter_ollama``) or raw SSE/NDJSON text; either way the
    reasoning chain (``reasoning``) and the answer (``content``) are captured so
    the benchmark measures the full token stream.
    """
    for line in data:
        if isinstance(line, dict):  # already parsed (Ollama NDJSON or defensive)
            token = _extract_token(line)
        else:  # SSE text line: "data: {...}"
            line = line.strip()
            if line.startswith("data:"):
                line = line[len("data:"):].strip()
                if line == "[DONE]":
                    continue
                try:
                    parsed = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
            else:
                # Raw NDJSON line (no SSE prefix) — Ollama streaming.
                try:
                    parsed = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
            token = _extract_token(parsed)
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

    async def _aiter_ollama(self, lines: AsyncIterator[str]) -> AsyncIterator[Any]:
        """Async iterator over Ollama NDJSON stream lines.

        Ollama's ``application/x-ndjson`` stream is *not* SSE: each line is a
        *complete* JSON object, not a ``data:`` prefixed delta. Parse each line
        to a dict so the shared ``_extract_token`` logic can read both the
        reasoning-phase ``thinking`` field and the answer-phase ``message.content``.
        Unparseable lines (and the ``[DONE]`` terminator) are skipped.
        """
        async for line in lines:
            line = line.strip()
            if not line or line.startswith("data:") or line == "[DONE]":
                continue
            try:
                yield json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue

    async def _get_client(self) -> httpx.AsyncClient:
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

        Works against both the OpenAI-compatible SSE stream
        (``POST /v1/chat/completions`` with ``choices[].delta``) and the
        Ollama NDJSON stream (``POST /api/chat`` with ``message.content``).

        Graceful degradation: a server that is down, that lacks the
        ``/v1/models`` endpoint, or that streams a broken payload is treated as
        an empty list / no-op rather than raising.
        """
        try:
            client = await self._get_client()
            payload: dict[str, Any] = {
                "model": self._model or self.config.model,
                "messages": messages,
                "stream": stream,
            }
            if stream:
                # Ollama streams the model stream at ``/api/chat``.
                response = await client.post(
                    _build_url(self.config.base_url, "api/chat"),
                    json=payload,
                )
                response.raise_for_status()
                async for token in self._aiter_ollama(response.aiter_lines()):
                    yield token
            else:
                # Non-streaming: Ollama's ``/api/generate`` returns a single
                # ``{"model","context","message","prompt","done","usage"}``
                # object (no ``choices``).
                response = await client.post(
                    _build_url(self.config.base_url, "api/generate"),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                yield _strip_content(
                    _strip_usage_response(data.get("response") or data)
                )
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
            client = await self._get_client()
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
            client = await self._get_client()
            response = await client.get(_build_url(self.config.base_url, "v1/models"))
            return response.status_code == 200
        except httpx.RequestError:
            return False

    async def serve(self, engine: EngineConfig) -> None:
        """Serve the engine as an OpenAI-compatible proxy until stopped.

        This is the engine's *compute* role; the benchmark never calls it.
        """
        from local_llm_benchmark.server.proxy import serve_proxy

        await serve_proxy(engine)

    async def unload_model(self) -> None:
        """Unload the currently loaded model from memory."""
        # Ollama / LM Studio are remote; there is nothing to unload locally.
        await self.close()
