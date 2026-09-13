"""OpenAI-compatible proxy.

``--serve`` blocks here and exposes the local engine as an OpenAI-compatible
API, so it can itself be benchmarked as an engine under test.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException

from local_llm_benchmark.config import EngineConfig


async def _stream_response(
    source: httpx.ASyncStreamingResponse,
    request: dict,
) -> AsyncIterator[dict]:
    """Forward a streamed chunk from the source engine to the client."""
    async for chunk in source.aiter_lines():
        if not chunk:
            continue
        payload = {"id": request.get("id", "cmpl-1"), "object": "chat.completion.chunk"}
        if request.get("stream"):
            payload["choices"] = [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": chunk},
                    "finish_reason": None,
                }
            ]
        else:
            payload["choices"] = [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": chunk},
                    "finish_reason": None,
                }
            ]
        yield payload


async def _forward(
    engine: EngineConfig,
    body: dict,
) -> Any:
    """Forward a chat-completions request to the source engine."""
    client = httpx.AsyncClient(timeout=engine.timeout)
    try:
        response = await client.post(
            _build_url(engine.base_url, "v1/chat/completions"),
            json=body,
        )
        response.raise_for_status()
        if body.get("stream"):
            return httpx.AsyncStreamingResponse(
                _stream_response(response.aiter_lines(), body),
                media_type="text/event-stream",
            )
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc)) from exc
    finally:
        await client.aclose()


async def _handle_chat(body: dict) -> Any:
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    data = await _forward(_engine, {"messages": messages, "stream": stream})
    if stream:
        return data
    return _strip_usage_response(data)


async def _handle_models() -> Any:
    data = await _forward(_engine, {"stream": False})
    return {"data": [data]}


# The active source engine.
_engine: EngineConfig | None = None


def install(engine: EngineConfig) -> FastAPI:
    """Install *engine* as the active proxy source and return the app."""
    global _engine
    _engine = engine
    app = FastAPI(title="Local LLM Engine Proxy")

    @app.get("/v1/models")
    async def list_models() -> Any:
        return await _handle_models()

    @app.post("/v1/chat/completions")
    async def chat_completions(body: dict) -> Any:
        return await _handle_chat(body)

    return app


async def serve_proxy(engine: EngineConfig) -> None:
    """Serve *engine* as an OpenAI-compatible proxy until interrupted."""
    app = install(engine)
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()
