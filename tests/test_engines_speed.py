"""Tests for the OpenAI-compatible engine backend and the speed benchmark.

Uses a fake ``httpx.AsyncClient`` so no real network calls happen. The fake
client is injected into the engine by patching ``OpenAICompatEngine._get_client``
to return it, which is far more precise than patching httpx at the transport
level and lets us assert on the exact request payloads.
"""

from unittest.mock import AsyncMock

import anyio
import httpx
import pytest

from local_llm_benchmark.benchmarks.speed import benchmark_speed
from local_llm_benchmark.config import BenchmarkConfig, EngineConfig
from local_llm_benchmark.engines.openai_compat import OpenAICompatEngine


async def _collect(chat, messages, *, max_tokens):
    """Collect streamed tokens into a list."""
    return [token async for token in chat(messages, max_tokens=max_tokens)]


def _engine():
    return OpenAICompatEngine(EngineConfig("engine", "http://engine:11434", "model"))


class FakeStreamingResponse:
    """A fake SSE stream yielding one token per line."""

    def __init__(self, tokens):
        self._tokens = tokens

    def iter_lines(self):
        for token in self._tokens:
            yield f"data: {token}\n"


def _fake_client(response_factory):
    """Build a fake AsyncClient backed by a custom transport.

    In httpx >= 0.28 the ``post=`` / ``get=`` constructor arguments were
    removed, so a custom transport is used instead. ``response_factory(url,
    body)`` returns an ``httpx.Response``.
    """

    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.json() if request.content else None
        return response_factory(request.url, body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_chat_streams_tokens(monkeypatch):
    import anyio

    engine = _engine()

    async def fake_post(url, json=None):
        return httpx.Response(
            200,
            content=b"data: {\"choices\": [{\"delta\": {\"content\": \"Hi\"}}]}\n",
            headers={"content-type": "text/event-stream"},
        )

    monkeypatch.setattr(engine, "_get_client", AsyncMock(return_value=_fake_client(fake_post)))
    tokens = anyio.run(_collect(engine.chat, [{"role": "user", "content": "hi"}], max_tokens=10))
    assert tokens == ["Hi"]


def test_chat_non_streaming_returns_content(monkeypatch):
    engine = _engine()

    async def fake_post(url, json=None):
        assert json["stream"] is False
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "answer", "reasoning": "none"}, "finish_reason": "stop"}]
            },
        )

    monkeypatch.setattr(engine, "_get_client", AsyncMock(return_value=_fake_client(fake_post)))
    assert engine.chat_completed([{"role": "user", "content": "q"}], max_tokens=10) == "answer"


def test_chat_reasoning_field_captured(monkeypatch):
    """Engines like Ollama put output in ``reasoning``; it must be captured."""
    engine = _engine()

    async def fake_post(url, json=None):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": None, "reasoning": "the answer"}}]},
        )

    monkeypatch.setattr(engine, "_get_client", AsyncMock(return_value=_fake_client(fake_post)))
    tokens = anyio.run(_collect(engine.chat, [{}], max_tokens=10))
    assert tokens == ["the answer"]


def test_chat_downstream_error_degrades(monkeypatch):
    """A 500 response must not raise; chat yields nothing."""
    engine = _engine()

    async def fake_post(url, json=None):
        return httpx.Response(500, text="boom")

    monkeypatch.setattr(engine, "_get_client", AsyncMock(return_value=_fake_client(fake_post)))
    tokens = anyio.run(_collect(engine.chat, [{}], max_tokens=10))
    assert tokens == []


def test_chat_bad_json_degrades(monkeypatch):
    engine = _engine()

    async def fake_post(url, json=None):
        return httpx.Response(200, content=b"not-json")

    monkeypatch.setattr(engine, "_get_client", AsyncMock(return_value=_fake_client(fake_post)))
    tokens = anyio.run(_collect(engine.chat, [{}], max_tokens=10))
    assert tokens == []


def test_list_models(monkeypatch):
    engine = _engine()

    async def fake_get(url):
        return httpx.Response(
            200,
            json={"data": [{"id": "llama3"}, {"id": ""}, {"id": "mistral"}]},
        )

    monkeypatch.setattr(engine, "_get_client", AsyncMock(return_value=_fake_client(fake_get)))
    assert engine.list_models() == ["llama3", "mistral"]


def test_list_models_missing_endpoint(monkeypatch):
    engine = _engine()

    async def fake_get(url):
        return httpx.Response(404)

    monkeypatch.setattr(engine, "_get_client", AsyncMock(return_value=_fake_client(fake_get)))
    assert engine.list_models() == []


def test_models_available():
    engine = _engine()
    assert engine.models_available() is False


def test_close_idempotent(monkeypatch):
    engine = _engine()
    close = AsyncMock()
    monkeypatch.setattr(engine, "_get_client", AsyncMock(return_value=_fake_client(lambda *a, **k: httpx.Response(200))))
    anyio.run(engine.close)
    anyio.run(engine.close)
    assert engine._client is None
    assert engine._client.aclose.await_count == 1


def test_client_reused_across_requests(monkeypatch):
    """The engine lazily creates one client and reuses it."""
    engine = _engine()
    clients = []

    async def get_client():
        client = httpx.AsyncClient()
        clients.append(client)
        return client

    monkeypatch.setattr(engine, "_get_client", AsyncMock(side_effect=get_client))
    anyio.run(engine.chat, [{}], max_tokens=1)
    anyio.run(engine.chat, [{}], max_tokens=1)
    assert len(clients) == 1


def test_build_uses_openai_compat():
    from local_llm_benchmark.config import EngineConfig
    from local_llm_benchmark.engines.base import Engine

    engine = Engine.build(EngineConfig("e", "http://x:1", "m"))
    assert isinstance(engine, OpenAICompatEngine)


# --- Speed benchmark --------------------------------------------------------

def _fake_engine():
    """An engine whose chat yields a fixed number of tokens instantly."""

    class Fake:
        config = EngineConfig("engine", "http://engine:1", "model")

        async def chat(self, messages, *, max_tokens, stream=True):
            for _ in range(4):
                yield "a"

    return Fake()


def test_benchmark_speed_produces_rows():
    import anyio

    engine = _fake_engine()
    task = type("T", (), {"prompt": "p", "id": "t", "category": "qa"})()
    rows = anyio.run(benchmark_speed, engine, task, max_tokens=4, trials=2)
    assert len(rows) == 2
    for row in rows:
        assert row.engine == "engine"
        assert row.model == "model"
        assert row.task_id == "t"
        assert row.tok_per_s >= 0
        assert row.iters_per_s >= 0


def test_benchmark_speed_system_prompt():
    import anyio

    engine = _fake_engine()

    class T:
        prompt = "p"
        id = "t"
        category = "qa"

    async def chat(self, messages, *, max_tokens, stream=True):
        assert messages[0]["role"] == "system"
        for _ in range(4):
            yield "a"

    engine.chat = chat
    anyio.run(benchmark_speed, engine, T(), max_tokens=4, trials=1)


def test_benchmark_speed_max_concurrent(monkeypatch):
    import anyio

    engine = _fake_engine()
    # Patch chat to record how many concurrent invocations overlap.
    active = {"max": 0, "cur": 0}

    async def slow_chat(self, messages, *, max_tokens, stream=True):
        active["cur"] += 1
        active["max"] = max(active["max"], active["cur"])
        try:
            await anyio.sleep(0)
        finally:
            active["cur"] -= 1
        for _ in range(4):
            yield "a"

    engine.chat = slow_chat
    anyio.run(benchmark_speed, engine, type("T", (), {"prompt": "p", "id": "t", "category": "qa"})(),
              max_tokens=4, trials=3, max_concurrent=2)
    assert active["max"] <= 2
